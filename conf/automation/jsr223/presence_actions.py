import urllib2
from java.time import ZonedDateTime

from shared.helper import rule, getItemState, itemLastChangeOlderThen, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged, getGroupMember
from shared.triggers import ItemStateChangeTrigger

from custom.presence import PresenceHelper


@rule("lights_indoor.py")
class ArrivingActionRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State"),
            ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state="OPEN")
        ]
        
    def execute(self, module, input):
        if getItemState("pOther_Automatic_State_Outdoorlights") != ON:
            return
          
        if input["event"].getItemName() == "pGF_Corridor_Openingcontact_Door_State":
            if itemLastChangeOlderThen("pGF_Corridor_Motiondetector_State", ZonedDateTime.now().minusMinutes(10)):
                sendCommandIfChanged("pGF_Corridor_Light_Ceiling_Powered",ON)
        elif input["event"].getItemState().intValue() == PresenceHelper.STATE_AWAY and input["oldState"].intValue() == PresenceHelper.STATE_MAYBE_PRESENT:
            sendCommandIfChanged("pGF_Corridor_Light_Ceiling_Powered",OFF)

@rule("presence_detection.py") 
class SleepingActionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State",state=PresenceHelper.STATE_SLEEPING)]
            
    def execute(self, module, input):
        sendCommandIfChanged("gIndoor_Lights", OFF)
        sendCommandIfChanged("gOutdoor_Terrace_Light_Hue_Color", OFF)
        sendCommandIfChanged("pOutdoor_Light_Automatic_Main_Switch", ON)
        
        for child in getGroupMember("gAll_Sockets"):
            if child.getName() == "pFF_Attic_Socket_Powered":
                continue
            sendCommandIfChanged(child, OFF)
    
