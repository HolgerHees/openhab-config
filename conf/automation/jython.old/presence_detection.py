from java.time import ZonedDateTime
from java.time.temporal import ChronoUnit
import threading

from shared.helper import log, rule, itemLastChangeOlderThen, itemLastChangeNewerThen, getItemState, getFilteredChildItems, getItemLastUpdate, getItemLastChange, postUpdate, postUpdateIfChanged, startTimer, getGroupMember, getGroupMemberChangeTrigger, NotificationHelper
from shared.triggers import ItemStateChangeTrigger, ItemCommandTrigger
from custom.presence import PresenceHelper


@rule()
class PresenceCache:
    _shared_lock = threading.Lock()
    _shared_presence = None
    _shared_arrive = None
    _shared_possible_arriving = False

    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOther_Presence_State") ]

    def execute(self, module, input):
        state = input['event'].getItemState().intValue()
        if state != PresenceCache._shared_presence:
            if state == PresenceHelper.STATE_AWAY:
                PresenceCache.setArriving(False)
            PresenceCache._shared_presence = state

    @staticmethod
    def setPresenceState(state, postUpdate=True):
        if state == PresenceHelper.STATE_AWAY:
            PresenceCache.setArriving(False)
        PresenceCache._shared_presence = state
        postUpdateIfChanged("pOther_Presence_State",PresenceCache._shared_presence)

    @staticmethod
    def getPresenceState():
        if PresenceCache._shared_presence is None:
            PresenceCache._shared_presence = getItemState("pOther_Presence_State").intValue()
        return PresenceCache._shared_presence

    @staticmethod
    def setArriving(state):
        PresenceCache.setPossibleArrive(False)
        if PresenceCache._shared_arrive is None:
            PresenceCache.getArriving()
        PresenceCache._shared_arrive = PresenceCache._shared_arrive + 1 if state else 0
        postUpdate("pOther_Presence_Arrive_State", PresenceCache._shared_arrive )

    @staticmethod
    def getArriving():
        if PresenceCache._shared_arrive is None:
            PresenceCache._shared_arrive = getItemState("pOther_Presence_Arrive_State").intValue()
        return PresenceCache._shared_arrive

    @staticmethod
    def setPossibleArrive(state):
        PresenceCache._shared_possible_arriving = state

    @staticmethod
    def isPossibleArriving():
        return PresenceCache._shared_possible_arriving

    @staticmethod
    def getLock():
        return PresenceCache._shared_lock


@rule()
class PresenceDetectionDoorCheck:
    def __init__(self):
        self.triggers = [
            # arrive
            ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state="OPEN"),
            ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Streedside_State",state="OPEN"),

            # leave
            ItemStateChangeTrigger("pGF_Corridor_Lock_State",state=1), # door locked
            ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Streedside_State",state="CLOSED")
        ]

        self.timer = None

    @staticmethod
    def isAllClosedAndLocked():
        # garage door is open
        if getItemState("pGF_Garage_Openingcontact_Door_Streedside_State") == OPEN:
            return False

        # front door is not locked
        if getItemState("pGF_Corridor_Lock_State").intValue() != 1:
            return False

        return True

    def _checkArrival(self, input):
        if input['event'].getItemName() == "pGF_Corridor_Openingcontact_Door_State":
            PresenceCache.setPossibleArrive(True)

        if PresenceCache.getPresenceState() == PresenceHelper.STATE_AWAY:
            PresenceCache.setPresenceState(PresenceHelper.STATE_MAYBE_PRESENT)

    def _checkLeaving(self, input = None):
        if PresenceCache.getPresenceState() != PresenceHelper.STATE_MAYBE_PRESENT:
            return

        if not PresenceDetectionDoorCheck.isAllClosedAndLocked():
            return

        if input is None:
            PresenceCache.setPresenceState(PresenceHelper.STATE_AWAY)
        else:
            # Lets wait for 60 seconds if another event happens, like front or garage door opened
            # 1. 'leaving' was triggered by closing garage door.
            # 1. 'leaving' was triggered by door lock event.
            self.timer = startTimer(self.log, 60, self._checkLeaving)

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        with PresenceCache.getLock():
            if input['event'].getItemName() in ["pGF_Corridor_Openingcontact_Door_State", "pGF_Garage_Openingcontact_Door_Streedside_State"] and input['event'].getItemState() == OPEN:
                self._checkArrival(input)
            else:
                self._checkLeaving(input['event'].getItemName())

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
                lastUpdateDiff = ChronoUnit.SECONDS.between(getItemLastUpdate("gIndoor_Lights"), ZonedDateTime.now())
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

        #startTimer(self.log, 1, self.test)

    #def test(self):
    #    postUpdate("pOther_Presence_Sandra_State_Raw", ON)
    #    #self.process("pOther_Presence_Sandra_State_Raw", "pOther_Presence_Sandra_State", OFF)

    def process(self, itemName, relatedItemName, itemState):
        with PresenceCache.getLock():
            postUpdate( relatedItemName ,itemState) # Item name without raw, is the real one

            presenceState = PresenceCache.getPresenceState()

            if itemState == ON:
                # only possible if we are away
                if presenceState in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                    PresenceCache.setPresenceState(PresenceHelper.STATE_PRESENT)
            else:
                # we must check child items instead of group item, because group item is updated too late
                if presenceState == PresenceHelper.STATE_PRESENT and len(getFilteredChildItems("gOther_Presence_State_Raw", ON)) == 0:
                    PresenceCache.setPresenceState(PresenceHelper.STATE_AWAY if PresenceDetectionDoorCheck.isAllClosedAndLocked() else PresenceHelper.STATE_MAYBE_PRESENT)

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        relatedItemName = itemName[:-4]

        newItemState = input['event'].getItemState()
        oldItemState = input['oldState']

        itemHasSkipTimer = ( itemName in self.skippedTimer )
        if itemHasSkipTimer:
            self.skippedTimer[itemName].cancel()
            del self.skippedTimer[itemName]

        # sometimes, phones are losing wifi connections because of their sleep mode
        if newItemState == OFF:
            if oldItemState == ON:
                if itemLastChangeOlderThen("pGF_Corridor_Openingcontact_Door_State",ZonedDateTime.now().minusMinutes(30)) and PresenceCache.getArriving() > 0:
                    # relatedItem state is still ON
                    #lastChangedState = getItemLastChange(relatedItemName)
                    #if itemLastChangeNewerThen("pGF_Corridor_Openingcontact_Door_State",lastChangedState.minusMinutes(15)):
                    self.skippedTimer[itemName] = startTimer(self.log, 7200, self.process, args = [ itemName, relatedItemName, newItemState ]) # 1 hour
                    NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, u"System", u"Delayed presence processing {} for {}".format(newItemState,itemName))
                    return
        else:
            if oldItemState == OFF and itemHasSkipTimer:
                NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, u"System", u"Cancel presence processing {} for {}".format(newItemState,itemName))
                return

        self.process(itemName, relatedItemName, newItemState)
          
    
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
        self.triggers = [ ItemCommandTrigger("pOther_Scene4",command="ON") ]
        #postUpdateIfChanged("pOther_Scene4", OFF)

    def execute(self, module, input):
        with PresenceCache.getLock():
            if PresenceCache.getPresenceState() in [PresenceHelper.STATE_MAYBE_PRESENT,PresenceHelper.STATE_PRESENT,PresenceHelper.STATE_MAYBE_SLEEPING]:
                PresenceCache.setPresenceState(PresenceHelper.STATE_SLEEPING)

            #postUpdate("pOther_Scene4", OFF)
