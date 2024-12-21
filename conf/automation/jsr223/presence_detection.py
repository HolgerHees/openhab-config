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
            ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State"),
            ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Streedside_State")
        ]

        self.timer = None

    def checkGaragePresence(self, checkInterval):
        with PresenceCache.getLock():
            if PresenceCache.getPresenceState() != PresenceHelper.STATE_MAYBE_PRESENT:
                self.timer = None
                return

            # DOOR STILL OPEN. => If reopened, time will be canceled and restarted from scratch
            if getItemState("pGF_Garage_Openingcontact_Door_Streedside_State") == OPEN:
                self.timer = startTimer(self.log, checkInterval, self.checkGaragePresence, args = [checkInterval])
                return

            PresenceCache.setPresenceState(PresenceHelper.STATE_AWAY)
            self.timer = None

    def checkFrontdoorPresence(self, checkInterval, checkTimeSlot, lastInteractionTime):
        with PresenceCache.getLock():
            if PresenceCache.getPresenceState() != PresenceHelper.STATE_MAYBE_PRESENT:
                self.timer = None
                return

            # DOOR STILL OPEN. => If reopened, time will be canceled and restarted from scratch
            if getItemState("pGF_Corridor_Openingcontact_Door_State") == OPEN:
                self.timer = startTimer(self.log, checkInterval, self.checkFrontdoorPresence, args = [checkInterval, checkTimeSlot, ZonedDateTime.now()])
                return

            newestInteractionTime = None
            for item in getGroupMember("gSensor_Indoor"):
                _update = getItemLastUpdate(item)
                if newestInteractionTime == None or _update.isAfter(newestInteractionTime):
                    newestInteractionTime = _update

            if newestInteractionTime.isAfter(lastInteractionTime):
                # guest has arrived
                self.timer = startTimer(self.log, 60, self.checkFrontdoorPresence, args = [60, 3600, newestInteractionTime ])
                return

            if ZonedDateTime.now().isAfter(lastInteractionTime.plusSeconds(checkTimeSlot)):
                PresenceCache.setPresenceState(PresenceHelper.STATE_AWAY)
                self.timer = None
                return

            self.timer = startTimer(self.log, checkInterval, self.checkFrontdoorPresence, args = [checkInterval, checkTimeSlot, lastInteractionTime])

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        with PresenceCache.getLock():
            if input['event'].getItemName() == "pGF_Corridor_Openingcontact_Door_State" and input['event'].getItemState() == OPEN:
                PresenceCache.setPossibleArrive(True)

            if PresenceCache.getPresenceState() not in [PresenceHelper.STATE_AWAY, PresenceHelper.STATE_MAYBE_PRESENT]:
                return

            if PresenceCache.getPresenceState() != PresenceHelper.STATE_MAYBE_PRESENT:
                PresenceCache.setPresenceState(PresenceHelper.STATE_MAYBE_PRESENT)

            if input['event'].getItemName() == "pGF_Corridor_Openingcontact_Door_State":
                self.timer = startTimer(self.log, 1, self.checkFrontdoorPresence, args = [1, 60, ZonedDateTime.now()])
            else:
                self.timer = startTimer(self.log, 300, self.checkGaragePresence, args = [300])

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

        #self.process("pOther_Presence_Sandra_State_Raw", "pOther_Presence_Sandra_State", ON)

    def process(self, itemName, relatedItemName, itemState):
        with PresenceCache.getLock():
            presenceState = PresenceCache.getPresenceState()

            if itemState == ON:
                postUpdate( relatedItemName ,ON) # Item name without raw, is the real one

                # only possible if we are away
                if presenceState in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                    PresenceCache.setPresenceState(PresenceHelper.STATE_PRESENT)
            else:
                postUpdate( relatedItemName ,OFF) # Item name without "_Raw", is the real one

                # we must check child items instead of group item, because group item is updated too late
                #if getItemState("gOther_Presence_State_Raw") == OFF:
                if len(getFilteredChildItems("gOther_Presence_State_Raw", ON)) == 0:
                    # only possible if we are present and not sleeping
                    if presenceState in [PresenceHelper.STATE_MAYBE_PRESENT,PresenceHelper.STATE_PRESENT]:
                        PresenceCache.setPresenceState(PresenceHelper.STATE_AWAY)

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
                    lastChangedState = getItemLastChange(relatedItemName)
                    if itemLastChangeNewerThen("pGF_Corridor_Openingcontact_Door_State",lastChangedState.minusMinutes(15)):
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
