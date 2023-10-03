import can
import cantools
from enum import Enum


class MsgName(Enum):
    ACT_CYCLE_TIME = 'ACT_CYCLE_TIME'
    SET_CYCLE_TIME = 'SET_CYCLE_TIME'
    ACT_STATUS_2 = 'ACT_STATUS_2'
    ACT_INSULATION_MON = 'ACT_INSULATION_MON'
    ACT_HW_LIM_MN = 'ACT_HW_LIM_MN'
    AVL_SYS_DEVICE_ID = 'AVL_SYS_DEVICE_ID'
    AVL_SYS_PART_ID = 'AVL_SYS_PART_ID'
    ACT_SET_RI_PWR = 'ACT_SET_RI_PWR'
    SET_RI_PWR = 'SET_RI_PWR'
    ACT_PWR_SWITCH_CTRL = 'ACT_PWR_SWITCH_CTRL'
    ACT_SET_SLOPE = 'ACT_SET_SLOPE'
    SET_SLOPE = 'SET_SLOPE'
    SET_VIRTUAL_IN = 'SET_VIRTUAL_IN'
    SET_DCH = 'SET_DCH'
    ACT_SET_DCH = 'ACT_SET_DCH'
    ACT_HW_MODE = 'ACT_HW_MODE'
    SET_LIM_MN = 'SET_LIM_MN'
    SET_LIM_MX = 'SET_LIM_MX'
    ACT_SET_LIM_MN = 'ACT_SET_LIM_MN'
    ACT_SET_LIM_MX = 'ACT_SET_LIM_MX'
    ACT_SET_U_I = 'ACT_SET_U_I'
    ACT_U_I = 'ACT_U_I'
    SET_SWITCH_CTRL = 'SET_SWITCH_CTRL'
    CLEARANCE = 'CLEARANCE'
    WD = 'WD'
    SET_U_I = 'SET_U_I'
    ACT_FAULT = 'ACT_FAULT'
    ACT_Q = 'ACT_Q'
    ACT_E = 'ACT_E'
    AVL_SYS_VER_SW = 'AVL_SYS_VER_SW',
    ACT_HW_LIM_MX = 'ACT_HW_LIM_MX'
    SET_SUPV_MX = 'SET_SUPV_MX'
    ACT_STATUS = 'ACT_STATUS'
    SET_SUPV_MN = 'SET_SUPV_MN'
    ACT_SUPV_MN = 'ACT_SUPV_MN'
    ACT_SUPV_MX = 'ACT_SUPV_MX'


class SetSwitch(Enum):
    OFF = 0
    STANDBY = 1
    ON = 2
    ERROR = 5


class SetCtrl(Enum):
    U = 1
    I = 2
    P = 3


class EstorageInterface(can.Listener):
    def __init__(self, n):
        self.num_sb = n
        self.db = cantools.database.load_file('avl_estorage_lv_v26.dbc')
        self.SET_U = 0.0
        self.SET_I = 0.0
        self.SET_LIM_U_MX = n * 14.0
        self.SET_LIM_U_MN = n * 8.0
        self.SET_LIM_I_MX = 40.0
        self.SET_LIM_I_MN = -40.0
        self.SET_LIM_PWR_MX = n*400.0
        self.SET_LIM_PWR_MN = -n*400.0
        self.SET_RI = 0.0
        self.SET_PWR = 0.0
        self.SET_U_SLOPE = 2.0
        self.SET_I_SLOPE = 10.0
        self.SET_PWR_SLOPE = 0.0
        self.SET_SWITCH = SetSwitch.OFF
        self.SET_CTRL = SetCtrl.I
        self.SUPV_U_MX = n * 16.0
        self.SUPV_U_MN = n * 5.0
        self.SUPV_I_MX = 50.0
        self.SUPV_I_MN = -50.0
        self.SUPV_PWR_MX = 900.0
        self.SUPV_PWR_MN = -900.0
        self.ACT_SWITCH = SetSwitch.OFF
        self.ACT_U = 0
        self.ACT_I = 0
        self.ACT_SET_U = 0
        self.ACT_SET_I = 0
        self.count100 = 0
        self.count10 = 0

    def send100Hz(self):
        id = 0
        data = 0
        if 1 == self.count100:
            msg = self.db.get_message_by_name(MsgName.SET_U_I.value)
            data = msg.encode({'SET_U': self.SET_U, 'SET_I': self.SET_I})
            id = msg.frame_id
        elif 3 == self.count100:
            msg = self.db.get_message_by_name(MsgName.SET_SWITCH_CTRL.value)
            data = msg.encode({'SET_SWITCH': self.SET_SWITCH.value, 
                            'SET_CTRL': self.SET_CTRL.value, 
                            'RST_E': 0, 
                            'RST_Q': 0})
            id = msg.frame_id
        elif 5 == self.count100:
            msg = self.db.get_message_by_name(MsgName.SET_RI_PWR.value)
            data = msg.encode({'SET_RI': self.SET_RI, 'SET_PWR': self.SET_PWR})
            id = msg.frame_id
        elif 7 == self.count100:
            msg = self.db.get_message_by_name(MsgName.SET_LIM_MX.value)
            data = msg.encode({'SET_LIM_U_MX': self.SET_LIM_U_MX, 
                            'SET_LIM_I_MX': self.SET_LIM_I_MX, 
                            'SET_LIM_PWR_MX': self.SET_LIM_PWR_MX})
            id = msg.frame_id
        elif 8 == self.count100:
            msg = self.db.get_message_by_name(MsgName.SET_LIM_MN.value)
            data = msg.encode({'SET_LIM_U_MN': self.SET_LIM_U_MN, 
                            'SET_LIM_I_MN': self.SET_LIM_I_MN, 
                            'SET_LIM_PWR_MN': self.SET_LIM_PWR_MN})
            id = msg.frame_id
        elif 9 == self.count100:
            self.count100 = 0
            return self.send10Hz()

        self.count100 = self.count100 + 1

        return can.Message(arbitration_id=id, data=data, is_extended_id=False)

    def send10Hz(self):
        id = 0
        data = 0
        if 1 == self.count10:
                msg = self.db.get_message_by_name(MsgName.SET_SUPV_MX.value)
                data = msg.encode({'SUPV_U_MX': self.SUPV_U_MX, 
                                'SUPV_I_MX': self.SUPV_I_MX, 
                                'SUPV_PWR_MX': self.SUPV_PWR_MX})
                id = msg.frame_id
        elif 3 == self.count10:
                msg = self.db.get_message_by_name(MsgName.SET_SUPV_MN.value)
                data = msg.encode({'SUPV_U_MN': self.SUPV_U_MN, 
                                'SUPV_I_MN': self.SUPV_I_MN, 
                                'SUPV_PWR_MN': self.SUPV_PWR_MN})
                id = msg.frame_id
        elif 5 == self.count10:
                msg = self.db.get_message_by_name(MsgName.SET_SLOPE.value)
                data = msg.encode({'SET_U_SLOPE': self.SET_U_SLOPE, 
                                    'SET_I_SLOPE': self.SET_I_SLOPE, 
                                    'SET_PWR_SLOPE': self.SET_PWR_SLOPE})
                id = msg.frame_id
        elif 7 == self.count10:
                msg = self.db.get_message_by_name(MsgName.CLEARANCE.value)
                data = msg.encode({'CLEARANCE': 1})
                id = msg.frame_id
        elif 9 == self.count10:
            self.count10 = 0
            return self.send1Hz()

        self.count10 = self.count10 + 1 

        return can.Message(arbitration_id=id, data=data, is_extended_id=False)


    def send1Hz(self):
        msg = self.db.get_message_by_name(MsgName.SET_CYCLE_TIME.value)
        data = msg.encode({'SET_MSRD_CYCLE': 10, 'SET_DEM_CYCLE': 10})
        id = msg.frame_id
 
        return can.Message(arbitration_id=id, data=data, is_extended_id=False)


    def on_message_received(self, msg):
        m = self.db.get_message_by_frame_id(msg.arbitration_id)
        if m.name == MsgName.ACT_U_I.value:
            data = m.decode(msg.data)
            self.ACT_U = data["ACT_U"]
            self.ACT_I = data["ACT_I"]
            self.SET_U = self.ACT_U
        if m.name == MsgName.ACT_SET_U_I.value:
            data = m.decode(msg.data)
            self.ACT_SET_U = data["ACT_SET_U"]
            self.ACT_SET_I = data["ACT_SET_I"]
        if  m.name == MsgName.ACT_PWR_SWITCH_CTRL.value:
            data = m.decode(msg.data)
            self.ACT_SWITCH = SetSwitch(data["ACT_SWITCH"])

