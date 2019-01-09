from marvin.helper import log, rule, createTimer, itemLastUpdateNewerThen, getNow, getFilteredChildItems, getGroupMember, getItemLastUpdate, getItemState, postUpdate, postUpdateIfChanged, sendCommand, sendNotification, getItemLastUpdate
from core.triggers import ItemStateChangeTrigger


@rule("presence_detection.py")
class PresenceCheckRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("State_Holger_Presence"),
            ItemStateChangeTrigger("State_Sandra_Presence")
        ]
        
    def execute(self, module, input):
        itemName = input['event'].getItemName()
        itemState = input['event'].getItemState()
        
        sendNotification(u"{}".format(itemName), u"{}".format(itemState))
        
        holgerPhone = itemState if itemName == "State_Holger_Presence" else getItemState("State_Holger_Presence")
        sandraPhone = itemState if itemName == "State_Sandra_Presence" else getItemState("State_Sandra_Presence")
        
        if holgerPhone == ON or sandraPhone == ON:
            if getItemState("State_Presence").intValue() == 0:
                postUpdate("State_Presence",1)
                sendNotification(u"Tür", u"Willkommen")
        else:
            if getItemState("State_Presence").intValue() != 0:
                postUpdate("State_Presence",0)
                lightMsg = u" - LICHT an" if getItemState("Lights_Indoor") != OFF else u""
                windowMsg = u" - FENSTER offen" if getItemState("Openingcontacts") != CLOSED else u""

                sendNotification(u"Tür", u"Auf Wiedersehen{}{}".format(lightMsg,windowMsg))

#@rule("presence_detection.py")
#class UnexpectedMotionRule:
#    def __init__(self):
#        self.triggers = [
#            ItemStateChangeTrigger("Motiondetector_FF_Floor",state="OPEN"),
#            ItemStateChangeTrigger("Motiondetector_FF_Livingroom",state="OPEN"),
#            ItemStateChangeTrigger("Motiondetector_SF_Floor",state="OPEN")
#        ]

#    def execute(self, module, input):
#        if getItemState("State_Presence").intValue() == 0:
#            sendNotification(u"Unexpected Motion", u"{}".format(input['event'].getItemName()))

@rule("presence_detection.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Motiondetector_FF_Floor",state="OPEN"),
            ItemStateChangeTrigger("Motiondetector_FF_Livingroom",state="OPEN"),
            ItemStateChangeTrigger("Motiondetector_SF_Floor",state="OPEN"),
            ItemStateChangeTrigger("Lights_FF",state="ON"),
            ItemStateChangeTrigger("Shutters_FF",state="0")
        ]

    def execute(self, module, input):
        if getItemState("State_Presence").intValue() == 2:
            if getItemState("TV_Online") == ON or getItemState("Lights_FF") == ON or getItemState("Shutters_FF") == PercentType.ZERO:
                postUpdate("State_Presence", 1)

@rule("presence_detection.py") 
class SleepingRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("Scene4",state="ON") ]

    def execute(self, module, input):
        if getItemState("State_Presence").intValue() == 1:
            postUpdate("State_Presence", 2)
            
        postUpdate("Scene4", OFF)
