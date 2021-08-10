import urllib2
from java.time import ZonedDateTime

from shared.helper import rule, getItemState, itemLastChangeOlderThen, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged, createTimer, getGroupMember
from shared.triggers import ItemStateChangeTrigger


@rule("presence_actions.py")
class LeavingActionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State")]

    def execute(self, module, input):
        #self.log.info("test")
        #self.log.info("{}".format(input["event"].getItemState()))
        if input["event"].getItemState().intValue() == 1:
            postUpdateIfChanged("pOther_Manual_State_Notify", OFF)
        else:
            postUpdateIfChanged("pOther_Manual_State_Notify", ON)

@rule("lights_indoor.py")
class ArrivingActionRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State"),
            ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state="OPEN")
        ]
        self.isArriving = False
        self.arrivingTimer = None

    def arrivingCallback(self):
        self.isArriving = False
    
    def execute(self, module, input):
        if input["event"].getItemName() == "pGF_Corridor_Openingcontact_Door_State":
            if self.isArriving:
                if getItemState("pOther_Automatic_State_Outdoorlights") == ON:
                    sendCommand("pGF_Corridor_Light_Ceiling_Powered",ON)
                self.isArriving = False
        # 10 minutes matches the max time ranges used by presence detection to ping phones => see pingdevice thing configuration
        # it can happen that pOther_Presence_State changes after pGF_Corridor_Openingcontact_Door_State was opened
        elif itemLastChangeOlderThen("pGF_Corridor_Openingcontact_Door_State", ZonedDateTime.now().minusMinutes(10)):
            self.isArriving = input["event"].getItemState().intValue() == 1 and input["oldState"].intValue() == 0
            if self.isArriving:
                self.arrivingTimer = createTimer(self.log, 60, self.arrivingCallback )
                self.arrivingTimer.start()

@rule("presence_detection.py") 
class SleepingActionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State",state="2")]
            
    def execute(self, module, input):
        sendCommandIfChanged("gIndoor_Lights", OFF)
        sendCommandIfChanged("pOutdoor_Light_Automatic_Main_Switch", ON)
        
        for child in getGroupMember("gAll_Sockets"):
            if child.getName() == "pFF_Attic_Socket_Powered":
                continue
            sendCommandIfChanged(child, OFF)
    
