from java.time import ZonedDateTime
from java.time.temporal import ChronoUnit
import threading

from shared.helper import log, rule, itemLastChangeOlderThen, getItem, getItemState, getFilteredChildItems, getItemLastUpdate, postUpdate, postUpdateIfChanged, startTimer, isMember, getGroupMember, getGroupMemberChangeTrigger, NotificationHelper, UserHelper
from shared.triggers import ItemStateChangeTrigger
from custom.presence import PresenceHelper

class PresenceCache:
    _shared_lock = threading.Lock()
    _shared_presence = None
    _shared_possible_arriving = False
    _shared_arrive = None

    @staticmethod
    def getLock():
        return PresenceCache._shared_lock

    @staticmethod
    def getPresenceState():
        if PresenceCache._shared_presence is None:
            PresenceCache._shared_presence = getItemState("pOther_Presence_State").intValue()
        return PresenceCache._shared_presence

    @staticmethod
    def setPresenceState(state):
        if state == PresenceHelper.STATE_AWAY:
            PresenceCache.setArriving(False)
        PresenceCache._shared_presence = state
        postUpdateIfChanged("pOther_Presence_State",PresenceCache._shared_presence)

    @staticmethod
    def setArriving(state):
        PresenceCache.setPossibleArrive(False)
        if PresenceCache._shared_arrive is None:
            PresenceCache._shared_arrive = getItemState("pOther_Presence_Arrive_State").intValue()
        PresenceCache._shared_arrive = PresenceCache._shared_arrive + 1 if state else 0
        postUpdate("pOther_Presence_Arrive_State", PresenceCache._shared_arrive )

    @staticmethod
    def isPossibleArriving():
        return PresenceCache._shared_possible_arriving

    @staticmethod
    def setPossibleArrive(state):
        PresenceCache._shared_possible_arriving = state

@rule()
class PresenceDetectionDoorCheck:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State", "OPEN"),
            ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Streedside_State", "OPEN")
        ]

        self.timer = None

        #postUpdate("pOther_Presence_Arrive_State",1)

    def checkGuestPresence(self, checkInterval, referenceTime, checkUntilTime ):
        with PresenceCache.getLock():
            if PresenceCache.getPresenceState() != PresenceHelper.STATE_MAYBE_PRESENT:
                self.timer = None
                return

            newestUpdate = None
            for item in getGroupMember("gSensor_Indoor"):
                _update = getItemLastUpdate(item)
                if newestUpdate == None or _update.isAfter(newestUpdate):
                    newestUpdate = _update

            if newestUpdate.isAfter(referenceTime):
                self.timer = startTimer(self.log, 60, self.checkGuestPresence, args = [60, newestUpdate, ZonedDateTime.now().plusSeconds(7200) ])
            else:
                if getItemState("pGF_Corridor_Openingcontact_Door_State") == OPEN:
                    checkUntilTime = ZonedDateTime.now().plusSeconds(60)

                if ZonedDateTime.now().isAfter(checkUntilTime):
                    PresenceCache.setPresenceState(PresenceHelper.STATE_AWAY)
                    self.timer = None
                else:
                    self.timer = startTimer(self.log, checkInterval, self.checkGuestPresence, args = [checkInterval, referenceTime, checkUntilTime])

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        with PresenceCache.getLock():
            if input['event'].getItemName() == "pGF_Corridor_Openingcontact_Door_State":
                PresenceCache.setPossibleArrive(True)

            if PresenceCache.getPresenceState() != PresenceHelper.STATE_AWAY:
                return

            PresenceCache.setPresenceState(PresenceHelper.STATE_MAYBE_PRESENT)
            self.timer = startTimer(self.log, 1, self.checkGuestPresence, args = [1, ZonedDateTime.now(), ZonedDateTime.now().plusSeconds( 300 if input['event'].getItemName() == "pGF_Garage_Openingcontact_Door_Streedside_State" else 60 )])

@rule()
class PresenceDetectionMovingCheck:
    def __init__(self):
        self.triggers = getGroupMemberChangeTrigger("gSensor_Indoor")

        self.timer = None

    def checkSleeping(self):
        with PresenceCache.getLock():
            if PresenceCache.getPresenceState() != PresenceHelper.STATE_MAYBE_SLEEPING:
                self.timer = None
                return

            if getItemState("gIndoor_Lights") == ON:
                self.timer = startTimer(self.log, 60, self.checkSleeping)
            else:
                lastUpdateDiff = ChronoUnit.SECONDS.between(getItemLastUpdate("gIndoor_Lights"),ZonedDateTime.now())
                if lastUpdateDiff >= 600:
                    PresenceCache.setPresenceState(PresenceHelper.STATE_SLEEPING)
                    self.timer = None
                else:
                    self.timer = startTimer(self.log, 60, self.checkSleeping)

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        with PresenceCache.getLock():
            if PresenceCache.isPossibleArriving():
                PresenceCache.setArriving(True)

            if PresenceCache.getPresenceState() == PresenceHelper.STATE_SLEEPING:
                PresenceCache.setPresenceState(PresenceHelper.STATE_MAYBE_SLEEPING)

                # must be decoupled, to release lock
                self.timer = startTimer(self.log, 1, self.checkSleeping)

@rule()
class PresenceDetectionKnownPersonCheck:
    def __init__(self):
        self.triggers = getGroupMemberChangeTrigger("gOther_Presence_State_Raw")

        self.skippedTimer = {}

    def process(self,itemName,itemState):
        with PresenceCache.getLock():
            presenceState = PresenceCache.getPresenceState()

            if itemState == ON:
                postUpdate( itemName[:-4] ,ON) # Item name without raw, is the real one

                # only possible if we are away
                if presenceState in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                    PresenceCache.setPresenceState(PresenceHelper.STATE_PRESENT)
            else:
                postUpdate( itemName[:-4] ,OFF) # Item name without "_Raw", is the real one

                # we must check child items instead of group item, because group item is updated too late
                #if getItemState("gOther_Presence_State_Raw") == OFF:
                if len(getFilteredChildItems("gOther_Presence_State_Raw", ON)) == 0:
                    # only possible if we are present and not sleeping
                    if presenceState in [PresenceHelper.STATE_MAYBE_PRESENT,PresenceHelper.STATE_PRESENT]:
                        PresenceCache.setPresenceState(PresenceHelper.STATE_AWAY)

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        newItemState = input['event'].getItemState()
        oldItemState = input['oldState']

        if itemName in self.skippedTimer:
            self.skippedTimer[itemName].cancel()
            del self.skippedTimer[itemName]

        # sometimes, phones are losing wifi connections because of their sleep mode
        if newItemState == OFF:
            if oldItemState == ON:
                if itemLastChangeOlderThen("pGF_Corridor_Openingcontact_Door_State",ZonedDateTime.now().minusMinutes(30)):
                    self.skippedTimer[itemName] = startTimer(self.log, 7200, self.process, args = [ itemName, newItemState ]) # 1 hour
                    NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, u"System", u"Delayed presence processing {} for {}".format(newItemState,itemName))
                    return
        else:
            if oldItemState == OFF and itemName in self.skippedTimer:
                NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, u"System", u"Cancel presence processing {} for {}".format(newItemState,itemName))
                return
              
        self.process(itemName, newItemState)
          
    
@rule()
class PresenceDetectionWakeup:
    def __init__(self):
        self.triggers = [
            #ItemStateChangeTrigger("pGF_Corridor_Motiondetector_State",state="OPEN"),
            #ItemStateChangeTrigger("pGF_Livingroom_Motiondetector_State",state="OPEN"),
            #ItemStateChangeTrigger("pFF_Corridor_Motiondetector_State",state="OPEN"),
            ItemStateChangeTrigger("gGF_Lights",state="ON"),
            ItemStateChangeTrigger("gGF_Shutters",state="UP"),
            ItemStateChangeTrigger("gGF_Shutters",state="0")
        ]
        self.timer = None

    def wakeup(self):
        PresenceCache.setPresenceState(PresenceHelper.STATE_PRESENT)
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"System", u"Guten Morgen")

    def delayedWakeup(self, checkCounter ):
        if getItemState("gGF_Lights") == ON:
            with PresenceCache.getLock():
                if PresenceCache.getPresenceState() in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                    lightCount = 0
                    for child in getGroupMember("gGF_Lights"):
                        if child.getStateAs(OnOffType) == ON:
                            lightCount = lightCount + 1
                    # Signs (in first floor) for wake up are
                    # - a light is ON for more then 10 minutes
                    # - or more then 2 lights in total are ON
                    if checkCounter == 20 or lightCount > 2:
                        self.wakeup()
                        self.timer = None
                    else:
                        self.timer = startTimer(self.log, 30, self.delayedWakeup, args = [ checkCounter + 1 ])
        else:
            self.timer = None
        
    def execute(self, module, input):        
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        with PresenceCache.getLock():
            if PresenceCache.getPresenceState() in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                # sometimes the "gGF_Lights" state switches back and forth for a couple of milliseconds when set "gGF_Lights" state to OFF
                #if itemLastChangeOlderThen("pOther_Presence_State",ZonedDateTime.now().minusSeconds(5)):
                if input['event'].getItemName() == "gGF_Shutters":
                    self.wakeup()
                else:
                    self.timer = startTimer(self.log, 30, self.delayedWakeup, args = [ 0 ])


@rule()
class PresenceDetectionSleeping:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOther_Scene4",state="ON") ]

    def execute(self, module, input):
        with PresenceCache.getLock():
            if PresenceCache.getPresenceState() in [PresenceHelper.STATE_MAYBE_PRESENT,PresenceHelper.STATE_PRESENT,PresenceHelper.STATE_MAYBE_SLEEPING]:
                PresenceCache.setPresenceState(PresenceHelper.STATE_SLEEPING)

            postUpdate("pOther_Scene4", OFF)
