from custom.helper import log, rule, itemLastChangeOlderThen, getNow, getItemState, postUpdate, sendNotification, startTimer, getGroupMember
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
        
        #sendNotification(u"{}".format(itemName), u"{}".format(itemState), recipient='bot1')
        
        holgerPhone = itemState if itemName == "State_Holger_Presence" else getItemState("State_Holger_Presence")
        sandraPhone = itemState if itemName == "State_Sandra_Presence" else getItemState("State_Sandra_Presence")
        
        bot = 'bot1' if itemName == "State_Holger_Presence" else 'bot2'
        
        if holgerPhone == ON or sandraPhone == ON:
            # only possible if we are away
            if getItemState("State_Presence").intValue() == 0:
                postUpdate("State_Presence",1)
        else:
            # only possible if we are present and not sleeping
            if getItemState("State_Presence").intValue() == 1:
                postUpdate("State_Presence",0)

        if itemState == ON:
            sendNotification(u"Tür", u"Willkommen", recipient=bot)
        else:
            if holgerPhone == OFF and sandraPhone == OFF:
                lightMsg = u" - LICHT an" if getItemState("Lights_Indoor") != OFF else u""
                windowMsg = u" - FENSTER offen" if getItemState("Openingcontacts") != CLOSED else u""
                sendNotification(u"Tür", u"Auf Wiedersehen{}{}".format(lightMsg,windowMsg), recipient=bot)
            else:
                sendNotification(u"Tür", u"Auf Wiedersehen", recipient=bot)
        
@rule("presence_detection.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [
            #ItemStateChangeTrigger("Motiondetector_FF_Floor",state="OPEN"),
            #ItemStateChangeTrigger("Motiondetector_FF_Livingroom",state="OPEN"),
            #ItemStateChangeTrigger("Motiondetector_SF_Floor",state="OPEN"),
            ItemStateChangeTrigger("Lights_FF",state="ON"),
            ItemStateChangeTrigger("Shutters_FF",state="0")
        ]
        self.checkTimer = None
        
    def wakeup(self):
        if getItemState("State_Presence").intValue() == 2:
            postUpdate("State_Presence", 1)
            sendNotification(u"System", u"Guten Morgen")

    def delayedWakeup(self, checkCounter ):
        if getItemState("Lights_FF") == ON:
            lightCount = 0
            for child in getGroupMember("Lights_FF"):
                if getItemState(child) == ON:
                    lightCount = lightCount + 1
            # Signs (in first floor) for wake up are 
            # - a light is ON for more then 10 minutes 
            # - or more then 2 lights in total are ON
            if checkCounter == 20 or lightCount > 2:
                self.checkTimer = None                    
                self.wakeup()
            else:
                self.checkTimer = startTimer(self.log, 30, self.delayedWakeup, args = [ checkCounter + 1 ], oldTimer = self.checkTimer)
        else:
            self.checkTimer = None                    
        
    def execute(self, module, input):        
        # only possible if we are sleeping
        if getItemState("State_Presence").intValue() == 2:
            # sometimes the "Lights_FF" state switches back and forth for a couple of milliseconds when set "Lights_FF" state to OFF
            #if itemLastChangeOlderThen("State_Presence",getNow().minusSeconds(5)):
            if input['event'].getItemName() == "Shutters_FF":
                if self.checkTimer != None:
                    self.checkTimer.cancel()
                    self.checkTimer = None                    
                self.wakeup()
            else:
                self.checkTimer = startTimer(self.log, 30, self.delayedWakeup, args = [ 0 ], oldTimer = self.checkTimer)

@rule("presence_detection.py") 
class SleepingRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("Scene4",state="ON") ]

    def execute(self, module, input):
        # only possible if we are present
        if getItemState("State_Presence").intValue() == 1:
            postUpdate("State_Presence", 2)
            
        postUpdate("Scene4", OFF)
