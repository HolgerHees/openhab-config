from java.time import ZonedDateTime

from shared.helper import log, rule, itemLastChangeOlderThen, getItem, getItemState, getItemLastUpdate, postUpdate, postUpdateIfChanged, sendNotification, sendNotificationToAllAdmins, startTimer, getGroupMember, getGroupMemberChangeTrigger
from shared.triggers import ItemStateChangeTrigger
from custom.presence import PresenceHelper

        
@rule("presence_detection.py")
class PresenceMovingCheckRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State") ]
        self.triggers += getGroupMemberChangeTrigger("gSensor_Indoor",state="OPEN")

        self.isConfirmed = False
        self.confirmTimer = None
        
        self.fallbackTimer = None

    def setState(self,state,isFallback):
        postUpdateIfChanged("pOther_Presence_State",state)
        if state == PresenceHelper.STATE_AWAY:
            sendNotification(u"System", u"Unbekannter Gast {}".format( u"verschwunden" if isFallback else u"gegangen" ))
        
    def checkState(self, presenceState):
        if presenceState == PresenceHelper.STATE_MAYBE_PRESENT:
            if self.isConfirmed:
                self.fallbackTimer = startTimer(self.log, 7200, self.setState, args = [ PresenceHelper.STATE_AWAY, True ]) # 1 hour
        elif presenceState == PresenceHelper.STATE_MAYBE_SLEEPING:
            self.fallbackTimer = startTimer(self.log, 600, self.setState, args = [ PresenceHelper.STATE_SLEEPING, True ]) # 10 min
        
    def confirmPresence(self):
        presenceState = getItemState("pOther_Presence_State").intValue()
      
        if presenceState != PresenceHelper.STATE_MAYBE_PRESENT:
            return
          
        newestUpdate = 0
        for item in getItem("gSensor_Indoor").getAllMembers():
            if getItemState(item) == OPEN:
                newestUpdate = ZonedDateTime.now().toInstant().toEpochMilli()
                break
              
            _update = getItemLastUpdate(item).toInstant().toEpochMilli()
            if _update > newestUpdate:
                newestUpdate = _update
            
        self.isConfirmed = newestUpdate >= ZonedDateTime.now().minusSeconds(7).toInstant().toEpochMilli()
        
        if self.isConfirmed:
            self.checkState(presenceState)
        else:
            self.setState( PresenceHelper.STATE_AWAY, False )
            
        self.confirmTimer = None

    def execute(self, module, input):
        if self.fallbackTimer != None:
            self.fallbackTimer.cancel()
            self.fallbackTimer = None 
            
        presenceState = getItemState("pOther_Presence_State").intValue()
            
        if input['event'].getItemName() == "pGF_Corridor_Openingcontact_Door_State":
            if self.confirmTimer != None:
                self.confirmTimer.cancel()
                self.confirmTimer = None 
                
            self.isConfirmed = False
             
            if input['event'].getItemState() == OPEN:
                if presenceState == PresenceHelper.STATE_AWAY:
                    postUpdate("pOther_Presence_State",PresenceHelper.STATE_MAYBE_PRESENT)
                    sendNotification(u"System", u"Unbekannter Gast gekommen")
            else:
                if presenceState == PresenceHelper.STATE_MAYBE_PRESENT:
                    # check in 15 seconds again if there was any move events
                    self.confirmTimer = startTimer(self.log, 15, self.confirmPresence)
        else:
            # move events during sleep, check function will be called during presence state update cycle
            if presenceState == PresenceHelper.STATE_SLEEPING:
                postUpdate("pOther_Presence_State",PresenceHelper.STATE_MAYBE_SLEEPING)
                return
            
            self.checkState(presenceState)

@rule("presence_detection.py")
class PresenceCheckRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_Holger_State"),
            ItemStateChangeTrigger("pOther_Presence_Sandra_State")
        ]
        
        self.skippedTimer = {}
        
    def process(self,itemName,itemState):
        presenceState = getItemState("pOther_Presence_State").intValue()
        
        #sendNotificationToAllAdmins(u"{}".format(itemName), u"{}".format(itemState))
        
        holgerPhone = itemState if itemName == "pOther_Presence_Holger_State" else getItemState("pOther_Presence_Holger_State")
        sandraPhone = itemState if itemName == "pOther_Presence_Sandra_State" else getItemState("pOther_Presence_Sandra_State")
        
        bot = PresenceHelper.getRecipientByStateItem(itemName)
        
        if holgerPhone == ON or sandraPhone == ON:
            # only possible if we are away
            if presenceState in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                postUpdate("pOther_Presence_State",PresenceHelper.STATE_PRESENT)
        else:
            # only possible if we are present and not sleeping
            if presenceState in [PresenceHelper.STATE_MAYBE_PRESENT,PresenceHelper.STATE_PRESENT]:
                postUpdate("pOther_Presence_State",PresenceHelper.STATE_AWAY)

        if itemState == ON:
            sendNotification(u"System", u"Willkommen", recipients = [bot])
        else:
            if holgerPhone == OFF and sandraPhone == OFF:
                lightMsg = u" - LICHT an" if getItemState("gIndoor_Lights") != OFF else u""
                windowMsg = u" - FENSTER offen" if getItemState("gOpeningcontacts") != CLOSED else u""
                sendNotification(u"System", u"Auf Wiedersehen{}{}".format(lightMsg,windowMsg), recipients = [bot])
            else:
                sendNotification(u"System", u"Auf Wiedersehen", recipients = [bot])

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        itemState = input['event'].getItemState()
        
        # sometimes, phones are losing wifi connections because of their sleep mode
        if itemState == OFF:
            if itemLastChangeOlderThen("pGF_Corridor_Openingcontact_Door_State",ZonedDateTime.now().minusMinutes(30)):
                self.skippedTimer[itemName] = startTimer(self.log, 7200, self.process, args = [ itemName,itemState ]) # 1 hour
                sendNotification(u"System", u"Delayed presence processing {} for {}".format(itemState,itemName), recipients = ['bot_holger'])
                return
        else:
            if itemName in self.skippedTimer:
                self.skippedTimer[itemName].cancel()
                del self.skippedTimer[itemName]
                sendNotification(u"System", u"Cancel presence processing {} for {}".format(itemState,itemName), recipients = ['bot_holger'])
                return
              
        self.process(itemName,itemState)
          
    
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
        if getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
            postUpdate("pOther_Presence_State", PresenceHelper.STATE_PRESENT)
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
        if getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
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
        if getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_MAYBE_PRESENT,PresenceHelper.STATE_PRESENT,PresenceHelper.STATE_MAYBE_SLEEPING]:
            postUpdate("pOther_Presence_State", PresenceHelper.STATE_SLEEPING)
            
        postUpdate("pOther_Scene4", OFF)
