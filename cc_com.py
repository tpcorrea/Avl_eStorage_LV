#!/usr/bin/python3
# -*- coding: iso-8859-1 -*-
import paho.mqtt.client as mqtt
import random

class Com_cc:
    # Connect when instance is created
    def __init__(self):
        self.broker_url = "192.168.12.206"  # Replace with IP if needed

        # Define clent name with random ID
        self.client = mqtt.Client(
            "SB-Controler-" + "{:d}".format(int(random.random() * 1e4))
        )

        # Conect do broker when element is created
        self.mqtt_client_connect()  # <-- Uncomment after debug self.mqtt_client_connect()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.connected_flag = True  # set flag
            print("Conectado")
            self.client.subscribe("cc/+")
            self.client.subscribe("CC/+")
            self.client.subscribe("+/soc")

        else:
            print("Bad connection Returned code=", rc)

    def mqtt_client_connect(self):
        # Welcome message
        print("Trying to connect...")

        self.client.connected_flag = False
        self.client.on_connect = self.on_connect

        self.client.connect(self.broker_url)
        print("Connected to: ", self.broker_url)
        self.client.on_message = self.on_message  # attach function to callback
        self.client.loop_start()


    def on_message(self, client, userdata, msg):
        """Handle received message from broker"""
        # Check if message comes from central Controler
        if (msg.topic == "cc/power"):
            self.power_on(bool(int(msg.payload)))
        if (msg.topic == "cc/error"):
            self.clear_error(bool(int(msg.payload)))
        if (msg.topic == "CC/state"):
            self.update_sb_state(int(msg.payload))
        if (msg.topic == "cc/iDischarge"):
            self.update_iDischarge(float(msg.payload))
        if (msg.topic == "cc/iCharge"):
            self.update_iCharge(float(msg.payload))
        if (msg.topic == "cc/cycle_time"):
            self.update_cycle_time(float(msg.payload))
        if (msg.topic == "cc/soc_max"):
            self.update_soc_max(float(msg.payload))
        if (msg.topic == "cc/soc_min"):
            self.update_soc_min(float(msg.payload))
        if (msg.topic.split("/")[1] == "soc"):
            s = msg.topic.split("/")[0]
            index = int(s.lstrip("SB"))
            self.update_soc(index, float(msg.payload)*100.0)

    def clear_error(self, value):
        return value

    def update_hil_Isource(self, value):
        return value

    def update_sb_state(self, sb_num ,value):
        return value

    def update_soc(self, value):
        return value

    def update_soc_max(self, value):
        return value

    def update_soc_min(self, value):
        return value

    def power_on(self, turn_on):
        return turn_on

