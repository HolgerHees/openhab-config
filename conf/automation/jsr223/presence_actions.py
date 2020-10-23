import urllib2

from custom.helper import rule, getNow, getItemState, itemLastChangeOlderThen, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged, createTimer, getGroupMember
from core.triggers import ItemStateChangeTrigger


@rule("presence_actions.py")
class LeavingActionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Presence")]

    def execute(self, module, input):
        #self.log.info("test")
        #self.log.info("{}".format(input["event"].getItemState()))
        if input["event"].getItemState().intValue() == 1:
            postUpdateIfChanged("State_Notify", OFF)
        else:
            postUpdateIfChanged("State_Notify", ON)

@rule("lights_indoor.py")
class ArrivingActionRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("State_Presence"),
            ItemStateChangeTrigger("Door_FF_Floor",state="OPEN")
        ]
        self.isArriving = False
        self.arrivingTimer = None

    def arrivingCallback(self):
        self.isArriving = False
    
    def execute(self, module, input):
        if input["event"].getItemName() == "Door_FF_Floor":
            if self.isArriving:
                if getItemState("State_Outdoorlights") == ON:
                    sendCommand("Light_FF_Floor_Ceiling",ON)
                self.isArriving = False
        # 10 minutes matches the max time ranges used by presence detection to ping phones => see pingdevice thing configuration
        # it can happen that State_Presence changes after Door_FF_Floor was opened
        elif itemLastChangeOlderThen("Door_FF_Floor", getNow().minusMinutes(10)):
            self.isArriving = input["event"].getItemState().intValue() == 1 and input["oldState"].intValue() == 0
            if self.isArriving:
                self.arrivingTimer = createTimer(self.log, 60, self.arrivingCallback )
                self.arrivingTimer.start()

@rule("presence_detection.py") 
class SleepingActionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Presence",state="2")]
            
    def execute(self, module, input):
        sendCommandIfChanged("Lights_Indoor", OFF)
        sendCommandIfChanged("Motiondetector_Outdoor_Switch", ON)
        
        for child in getGroupMember("Sockets"):
            if child.getName("Socket_Attic") == "":
                continue
            sendCommandIfChanged(child, OFF)
    
