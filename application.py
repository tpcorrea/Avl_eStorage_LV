#!/usr/bin/python3
# -*- coding: iso-8859-1 -*-

from eStorage import SetSwitch
from eStorage import SetCtrl
from eStorage import EstorageInterface
from cc_com import Com_cc
from enum import Enum
import can
import asyncio
import time
import csv


class StateApp(Enum):
    INIT = 0
    OFF = 2
    WAIT = 3
    STANDBY1 = 4
    STANDBY2 = 5
    DISCHARGE = 6
    CHARGE = 7
    ERROR = 8

class StateSb(Enum):
    INIT = 0
    SET_COMM = 1
    OFF = 2
    PRECHARGE = 3
    STANDBY = 4
    ON = 5
    ERROR = 6

class Application:

    def __init__(self):
        # Store data into csv?
        self.store = True

        # Create objects of SB modules
        self.es = EstorageInterface(3)
        self.es.SET_CTRL = SetCtrl.I

        self.listeners = [self.es]

        # Period of periodic functions
        self.period_of_period_calls = 1
        self.period_fast_update = 0.001

        # Start CAN communication
        self.bus = can.interface.Bus(bustype='ixxat', channel=0, bitrate=1000000)

        # State machine act and set
        self.sb_state = StateSb.STANDBY
        self.turn_on = False
        self.control_on = True

        self.act_state = StateApp.INIT  # current state
        self.set_state = StateApp.INIT  # change to this state
        # dict with respective dict of transition functions
        # first state is current one and second is the state it will go to
        self.trans_function = {StateApp.INIT: {StateApp.OFF: None},
                               StateApp.OFF: {StateApp.WAIT: self.trans_OFF_TO_WAIT},
                               StateApp.WAIT: {StateApp.STANDBY1: self.trans_WAIT_TO_STANDBY},
                               StateApp.STANDBY1: {StateApp.STANDBY2: self.trans_STANDBY1_TO_STANDBY2},
                               StateApp.STANDBY2: {StateApp.DISCHARGE: self.trans_STANDBY2_TO_DISCHARGE,
                                             StateApp.CHARGE: self.trans_STANDBY2_TO_CHARGE},
                               StateApp.DISCHARGE: {StateApp.OFF: self.trans_OTHERS_TO_OFF,
                                             StateApp.CHARGE: self.trans_DISCHARGE_TO_CHARGE,
                                             StateApp.ERROR: self.trans_ANY_TO_ERROR},
                               StateApp.CHARGE: {StateApp.OFF: self.trans_OTHERS_TO_OFF,
                                             StateApp.DISCHARGE: self.trans_CHARGE_TO_DISCHARGE,
                                             StateApp.ERROR: self.trans_ANY_TO_ERROR},
                               StateApp.ERROR: {StateApp.OFF: self.trans_ERROR_TO_OFF}
                               }
        # dict with verification if a transition should take place
        self.condition_function = {StateApp.INIT: self.check_INIT,
                                   StateApp.OFF: self.check_OFF,
                                   StateApp.WAIT: self.check_WAIT,
                                   StateApp.STANDBY1: self.check_STANDBY1,
                                   StateApp.STANDBY2: self.check_STANDBY2,
                                   StateApp.DISCHARGE: self.check_DISCHARGE,
                                   StateApp.CHARGE: self.check_CHARGE,
                                   StateApp.ERROR: self.check_ERROR,
                                   }
        self.number_of_checks = 0

        # Create object to communicate with Central Controller
        self.com_cc = Com_cc()
        self.com_cc.power_on = self.rcv_cc_power_cmd
        self.com_cc.update_sb_state = self.rcv_sb_state
        self.com_cc.update_soc = self.rcv_sb_soc
        self.com_cc.update_iDischarge = self.rcv_cc_update_iDischarge
        self.com_cc.update_iCharge = self.rcv_cc_update_iCharge
        self.com_cc.update_cycle_time = self.rcv_cc_update_cycle_time
        self.com_cc.update_soc_max = self.rcv_soc_max
        self.com_cc.update_soc_min = self.rcv_soc_min

        # charge and discharge current and cycle time (updated from NodeRed)
        self.iDischarge = -10
        self.iCharge = 10
        self.cycle_time = 100
        self.timer_count = 0
        self.timer_timeout = self.cycle_time/self.period_fast_update 
        self.soc = {}
        self.soc_max = 85.0
        self.soc_min = 70.0

# --------- Async Functions -------------
    async def _run(self):
        tasks = [self.run_state_machine(),
                 self.update_eStorage()]
        await asyncio.gather(*tasks)

    async def run_state_machine(self):
        while True:
            self.check()
            self.update_state()
            self.com_cc.client.publish("es/state",str(self.act_state.value))
            self.com_cc.client.publish("es/act_u",str(self.es.ACT_U))
            self.com_cc.client.publish("es/act_i",str(self.es.ACT_I))
            await asyncio.sleep(0.5 * self.period_of_period_calls)
        
    async def update_eStorage(self):
        while True:
            self.timer_count = self.timer_count + 1 
            if self.act_state == StateApp.STANDBY1 or self.act_state == StateApp.STANDBY2:
                self.es.SET_LIM_U_MN = self.es.ACT_U

            msg = self.es.send100Hz()
            
            
            if msg.arbitration_id != 0:
                try:
                    self.bus.send(msg)
                    pass
                except can.CanError:
                    print("Message NOT sent")
            await asyncio.sleep(self.period_fast_update)  # time to next transmission burst

    # --------------- CAN and CC communication ---------------
    def rcv_cc_update_iDischarge(self, value):
        self.iDischarge = value
        print("Discharge ", value)

    def rcv_cc_update_iCharge(self, value):
        self.iCharge = value
        print("Charge ", value)

    def rcv_cc_update_cycle_time(self, value):
        self.cycle_time = value
        self.timer_timeout = self.cycle_time/self.period_fast_update
        print("Cycle Time ", value)

    def rcv_sb_soc(self, sb_num, value):
        self.soc[sb_num] = value
    
    def rcv_cc_power_cmd(self, turn_on):
        self.turn_on = turn_on

    def rcv_sb_state(self, value):
        self.sb_state = StateSb(value)

    def rcv_soc_max(self, value):
        self.soc_max = value
        print("SoC max ", value)

    def rcv_soc_min(self, value):
        self.soc_min = value
        print("SoC min ", value)

    # --------------- State Machine functions ---------------
    def check(self):
        func = self.condition_function.get(self.act_state, None)
        self.number_of_checks += 1

        if func is not None:
            func()

    def update_state(self):
        #  a transition happens when set_state != act_state
        if self.act_state != self.set_state:
            # first, it gets the trans dict of the actual state
            trans_dict = self.trans_function.get(self.act_state, None)
            self.number_of_checks = 0
            # then, it gets the trans_func corresponding to the set_state
            if trans_dict is not None:
                func = trans_dict.get(self.set_state, None)
                # if a tran_func exists, call it
                if func is not None:
                    func()
            self.act_state = self.set_state
            print("state transition to {}".format(self.set_state))
 
    ################### trans functions called when a State transisiton happens ##################
    def trans_empty(self):
        pass

    def trans_OFF_TO_WAIT(self):
        self.timer_count = 0

    def trans_WAIT_TO_STANDBY(self):
        self.es.SET_SWITCH = SetSwitch.ON
        self.es.SET_CTRL = SetCtrl.U
        self.timer_count = 0

    def trans_STANDBY1_TO_STANDBY2(self):
        self.es.SET_CTRL = SetCtrl.I
        self.es.SET_I = 0
        self.timer_count = 0

    def trans_STANDBY2_TO_DISCHARGE(self):
        self.es.SET_LIM_U_MN = self.es.num_sb*10
        self.es.SET_I = self.iDischarge
        self.timer_count = 0

    def trans_STANDBY2_TO_CHARGE(self):
        self.es.SET_LIM_U_MN = self.es.num_sb*10
        self.es.SET_I = self.iCharge
        self.timer_count = 0

    def trans_DISCHARGE_TO_CHARGE(self):
        self.es.SET_I = self.iCharge
        self.timer_count = 0

    def trans_CHARGE_TO_DISCHARGE(self):
        self.es.SET_I = self.iDischarge
        self.timer_count = 0

    def trans_OTHERS_TO_OFF(self):
        self.es.SET_SWITCH = SetSwitch.OFF
        pass

    def trans_ERROR_TO_OFF(self):
        pass        

    def trans_ANY_TO_ERROR(self):
        self.es.SET_SWITCH = SetSwitch.OFF

    ################### check functions for changing State ##################
    def check_INIT(self):
        self.set_state = StateApp.OFF

    def check_OFF(self):
        if self.turn_on is True and self.sb_state is StateSb.ON:
            self.set_state = StateApp.WAIT
            print("state machine going to WAIT")
            return
        # Stay in OFF

    def check_WAIT(self):
        if self.timer_count >  10/self.period_fast_update:
            self.set_state = StateApp.STANDBY1
            print("state machine going to STANDBY1")
            return


    def check_STANDBY1(self):
        if self.es.ACT_SWITCH == SetSwitch.ON:
            self.set_state = StateApp.STANDBY2
            print("state machine going to STANDBY2")
            return
        if self.timer_count > 5/self.period_fast_update:
            self.set_state = StateApp.OFF
            print("TIMEOUT at STANDBY2")
            return

    def check_STANDBY2(self):
        if self.timer_count > 15/self.period_fast_update:
            self.set_state = StateApp.CHARGE
            print("state machine going to CHARGE")
            return

    def check_DISCHARGE(self):
        if self.turn_on is False:
            self.set_state = StateApp.OFF
            print("state machine going to OFF")
        elif self.timer_count > self.timer_timeout:
            self.set_state = StateApp.CHARGE
            print("state machine going to CHARGE")
        elif self.soc_min >= min(self.soc.values()):
            self.set_state = StateApp.CHARGE
            print("state machine going to CHARGE")

        
    def check_CHARGE(self):
        if self.turn_on is False:
            self.set_state = StateApp.OFF
            print("state machine going to OFF")
        elif self.timer_count > self.timer_timeout:
            self.set_state = StateApp.DISCHARGE
            print("state machine going to DISCHARGE")
        elif self.soc_max <= max(self.soc.values()):
            self.set_state = StateApp.DISCHARGE
            print("state machine going to DISCHARGE")


    def check_ERROR(self):
        if self.turn_on is False:
            self.set_state = StateApp.OFF
            print("state machine going to OFF")
