from shared.helper import log, rule, itemLastChangeOlderThen, getItemState, postUpdate, sendNotification, sendNotificationToAllAdmins, startTimer, getGroupMember
from custom.presence import PresenceHelper
from core.triggers import ItemStateChangeTrigger
from java.time import ZonedDateTime

@rule("presence_detection.py")
class PresenceCheckRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_Holger_State"),
            ItemStateChangeTrigger("pOther_Presence_Sandra_State")
        ]
        
        self.skippedStates = {}
        
    def execute(self, module, input):
        itemName = input['event'].getItemName()
        itemState = input['event'].getItemState()

        # sometimes, phones are losing wifi connections because of their sleep mode
        if itemState == OFF:
            if itemLastChangeOlderThen("pGF_Corridor_Openingcontact_Door_State",ZonedDateTime.now().minusMinutes(30)):
                self.skippedStates[itemName] = True
                sendNotification(u"Phone", u"Skipped state {} for {}".format(itemState,itemName), recipients = ['bot_holger'])
                return
        else:
            if itemName in self.skippedStates:
                del self.skippedStates[itemName]
                sendNotification(u"Phone", u"Skipped state {} for {}".format(itemState,itemName), recipients = ['bot_holger'])
                return
          
        #sendNotificationToAllAdmins(u"{}".format(itemName), u"{}".format(itemState))
        
        holgerPhone = itemState if itemName == "pOther_Presence_Holger_State" else getItemState("pOther_Presence_Holger_State")
        sandraPhone = itemState if itemName == "pOther_Presence_Sandra_State" else getItemState("pOther_Presence_Sandra_State")
        
        bot = PresenceHelper.getRecipientByStateItem(itemName)
        
        if holgerPhone == ON or sandraPhone == ON:
            # only possible if we are away
            if getItemState("pOther_Presence_State").intValue() == 0:
                postUpdate("pOther_Presence_State",1)
        else:
            # only possible if we are present and not sleeping
            if getItemState("pOther_Presence_State").intValue() == 1:
                postUpdate("pOther_Presence_State",0)

        if itemState == ON:
            sendNotification(u"Tür", u"Willkommen", recipients = [bot])
        else:
            if holgerPhone == OFF and sandraPhone == OFF:
                lightMsg = u" - LICHT an" if getItemState("gIndoor_Lights") != OFF else u""
                windowMsg = u" - FENSTER offen" if getItemState("gOpeningcontacts") != CLOSED else u""
                sendNotification(u"Tür", u"Auf Wiedersehen{}{}".format(lightMsg,windowMsg), recipients = [bot])
            else:
                sendNotification(u"Tür", u"Auf Wiedersehen", recipients = [bot])
        
@rule("presence_detection.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [
            #ItemStateChangeTrigger("pGF_Corridor_Motiondetector_State",state="OPEN"),
            #ItemStateChangeTrigger("pGF_Livingroom_Motiondetector_State",state="OPEN"),
            #ItemStateChangeTrigger("pFF_Corridor_Motiondetector_State",state="OPEN"),
            ItemStateChangeTrigger("gGF_Lights",state="ON"),
            ItemStateChangeTrigger("gGF_Shutters",state="UP"),
            ItemStateChangeTrigger("gGF_Shutters",state="0")
        ]
        self.checkTimer = None
        
    def wakeup(self):
        if getItemState("pOther_Presence_State").intValue() == 2:
            postUpdate("pOther_Presence_State", 1)
            sendNotification(u"System", u"Guten Morgen")

    def delayedWakeup(self, checkCounter ):
        if getItemState("gGF_Lights") == ON:
            lightCount = 0
            for child in getGroupMember("gGF_Lights"):
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
        if getItemState("pOther_Presence_State").intValue() == 2:
            # sometimes the "gGF_Lights" state switches back and forth for a couple of milliseconds when set "gGF_Lights" state to OFF
            #if itemLastChangeOlderThen("pOther_Presence_State",ZonedDateTime.now().minusSeconds(5)):
            if input['event'].getItemName() == "gGF_Shutters":
                if self.checkTimer != None:
                    self.checkTimer.cancel()
                    self.checkTimer = None                    
                self.wakeup()
            else:
                self.checkTimer = startTimer(self.log, 30, self.delayedWakeup, args = [ 0 ], oldTimer = self.checkTimer)

@rule("presence_detection.py") 
class SleepingRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOther_Scene4",state="ON") ]

    def execute(self, module, input):
        # only possible if we are present
        if getItemState("pOther_Presence_State").intValue() == 1:
            postUpdate("pOther_Presence_State", 2)
            
        postUpdate("pOther_Scene4", OFF)
