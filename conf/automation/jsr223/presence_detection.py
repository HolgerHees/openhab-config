from java.time import ZonedDateTime
from java.time.temporal import ChronoUnit

from shared.helper import log, rule, itemLastChangeOlderThen, getItem, getItemState, getFilteredChildItems, getItemLastUpdate, postUpdate, postUpdateIfChanged, startTimer, isMember, getGroupMember, getGroupMemberChangeTrigger, NotificationHelper, UserHelper
from shared.triggers import ItemStateChangeTrigger
from custom.presence import PresenceHelper


@rule("presence_detection.py")
class PresenceMovingCheckRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Doors")
        self.triggers += [ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State"), ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Streedside_State")]
        #self.triggers += getGroupMemberChangeTrigger("gSensor_Indoor",state="OPEN")

        self.isConfirmed = False
        self.confirmTimer = None
        
        self.fallbackTimer = None
        
        #seconds = ChronoUnit.SECONDS.between(getItemLastUpdate("gIndoor_Lights"),ZonedDateTime.now())
        #self.log.info(u"{}".format(seconds))
 
    def setAway(self):
        if getItemState("pOther_Presence_State").intValue() != PresenceHelper.STATE_MAYBE_PRESENT:
            return

        postUpdateIfChanged("pOther_Presence_State",PresenceHelper.STATE_AWAY)

    def delayedAwayCheck(self):
        self.fallbackTimer = startTimer(self.log, 7200, self.setAway, args = []) # 1 hour
      
    def confirmArriving(self):
        if getItemState("pOther_Presence_State").intValue() != PresenceHelper.STATE_MAYBE_PRESENT:
            return
          
        newestUpdate = None
        for item in getGroupMember("gSensor_Indoor"):
            if getItemState(item) == OPEN:
                newestUpdate = ZonedDateTime.now()
                break
              
            _update = getItemLastUpdate(item)
            if newestUpdate == None or _update.isAfter(newestUpdate):
                newestUpdate = _update
        
        ref = ZonedDateTime.now().minusSeconds(7)
        self.isConfirmed = newestUpdate.isAfter(ref) or newestUpdate.isEqual(ref)
        
        if self.isConfirmed:
            self.delayedAwayCheck()
        else:
            self.setAway()
            
        self.confirmTimer = None

    def setSleeping(self):
        postUpdateIfChanged("pOther_Presence_State",PresenceHelper.STATE_SLEEPING)

    def delayedSleepingCheck(self):
        if getItemState("pOther_Presence_State").intValue() != PresenceHelper.STATE_MAYBE_SLEEPING:
            return

        if self.fallbackTimer == None or getItemState("gIndoor_Lights") == ON:
            self.fallbackTimer = startTimer(self.log, 600, self.delayedSleepingCheck) # 10 min
        else:
            lastUpdateDiff = ChronoUnit.SECONDS.between(getItemLastUpdate("gIndoor_Lights"),ZonedDateTime.now())
            if lastUpdateDiff >= 600:
                self.setSleeping()
            else:
                self.fallbackTimer = startTimer(self.log, 600 - lastUpdateDiff, self.delayedSleepingCheck) # 10 min

    def execute(self, module, input):
        if self.fallbackTimer != None:
            self.fallbackTimer.cancel()
            self.fallbackTimer = None 
            
        presenceState = getItemState("pOther_Presence_State").intValue()
            
        if isMember(input['event'].getItemName(), "gGF_Sensor_Doors"):
            if self.confirmTimer != None:
                self.confirmTimer.cancel()
                self.confirmTimer = None 
                
            self.isConfirmed = False
             
            if input['event'].getItemState() == OPEN:
                if presenceState in [PresenceHelper.STATE_AWAY, PresenceHelper.STATE_SLEEPING]:
                    postUpdate("pOther_Presence_State",PresenceHelper.STATE_MAYBE_PRESENT)
            else:
                if presenceState == PresenceHelper.STATE_MAYBE_PRESENT:
                    # check in 15 seconds again if there was any move events
                    self.confirmTimer = startTimer(self.log, 15, self.confirmArriving)
        else:
            # move events during sleep, check function will be called during presence state update cycle
            if presenceState == PresenceHelper.STATE_SLEEPING:
                postUpdate("pOther_Presence_State",PresenceHelper.STATE_MAYBE_SLEEPING)
            elif presenceState == PresenceHelper.STATE_MAYBE_SLEEPING:
                self.delayedSleepingCheck()
            elif presenceState == PresenceHelper.STATE_MAYBE_PRESENT and self.isConfirmed:
                self.delayedAwayCheck()

@rule("presence_detection.py")
class PresenceCheckRule:
    def __init__(self):
        self.triggers = getGroupMemberChangeTrigger("gOther_Presence_State_Raw")

        self.skippedTimer = {}

    def process(self,itemName,itemState):
        presenceState = getItemState("pOther_Presence_State").intValue()
        
        if itemState == ON:
            postUpdate( itemName[:-4] ,ON) # Item name without raw, is the real one

            # only possible if we are away
            if presenceState in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                postUpdate("pOther_Presence_State",PresenceHelper.STATE_PRESENT)
        else:
            postUpdate( itemName[:-4] ,OFF) # Item name without "_Raw", is the real one

            # we must check child items instead of group item, because group item is updated too late
            #if getItemState("gOther_Presence_State_Raw") == OFF:
            if len(getFilteredChildItems("gOther_Presence_State_Raw", ON)) == 0:
                # only possible if we are present and not sleeping
                if presenceState in [PresenceHelper.STATE_MAYBE_PRESENT,PresenceHelper.STATE_PRESENT]:
                    postUpdate("pOther_Presence_State",PresenceHelper.STATE_AWAY)

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        newItemState = input['event'].getItemState()
        oldItemState = input['oldState']

        # sometimes, phones are losing wifi connections because of their sleep mode
        if newItemState == OFF:
            if oldItemState == ON:
                if itemLastChangeOlderThen("pGF_Corridor_Openingcontact_Door_State",ZonedDateTime.now().minusMinutes(30)):
                    pass
                    #self.skippedTimer[itemName] = startTimer(self.log, 7200, self.process, args = [ itemName,newItemState ]) # 1 hour
                    #NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, u"System", u"Delayed presence processing {} for {}".format(newItemState,itemName))
                    #return
        else:
            if oldItemState == OFF and itemName in self.skippedTimer:
                self.skippedTimer[itemName].cancel()
                del self.skippedTimer[itemName]
                NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, u"System", u"Cancel presence processing {} for {}".format(newItemState,itemName))
                return
              
        self.process(itemName,newItemState)
          
    
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

        #startTimer(self.log, 5, self.test)

    #def test(self):
    #    postUpdate("pOther_Presence_Holger_State_Raw", ON)
    #    postUpdate("pOther_Presence_Sandra_State_Raw", ON)

    def wakeup(self):
        postUpdate("pOther_Presence_State", PresenceHelper.STATE_PRESENT)
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"System", u"Guten Morgen")

    def delayedWakeup(self, checkCounter ):
        if getItemState("gGF_Lights") == ON:
            if getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                lightCount = 0
                for child in getGroupMember("gGF_Lights"):
                    if child.getStateAs(OnOffType) == ON:
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
