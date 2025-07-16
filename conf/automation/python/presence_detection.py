from openhab import rule, Registry, Timer
from openhab.triggers import ItemStateChangeTrigger, ItemCommandTrigger, GroupStateChangeTrigger

from shared.notification import NotificationHelper
from shared.toolbox import ToolboxHelper

from custom.presence import PresenceHelper

from datetime import datetime, timedelta
import threading

import scope


@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Presence_State")
    ]
)
class Cache:
    _shared_lock = threading.Lock()
    _shared_presence = None
    _shared_arrive = None
    _shared_possible_arriving = False

    def execute(self, module, input):
        state = input['event'].getItemState().intValue()
        if state != Cache._shared_presence:
            if state == PresenceHelper.STATE_AWAY:
                Cache.setArriving(False)
            Cache._shared_presence = state

    @staticmethod
    def setPresenceState(state):
        if state == PresenceHelper.STATE_AWAY:
            Cache.setArriving(False)
        Cache._shared_presence = state
        Registry.getItem("pOther_Presence_State").postUpdateIfDifferent(Cache._shared_presence)

    @staticmethod
    def getPresenceState():
        if Cache._shared_presence is None:
            Cache._shared_presence = Registry.getItemState("pOther_Presence_State").intValue()
        return Cache._shared_presence

    @staticmethod
    def setArriving(state):
        Cache.setPossibleArrive(False)
        if Cache._shared_arrive is None:
            Cache.getArriving()
        Cache._shared_arrive = Cache._shared_arrive + 1 if state else 0
        Registry.getItem("pOther_Presence_Arrive_State").postUpdate(Cache._shared_arrive )

    @staticmethod
    def getArriving():
        if Cache._shared_arrive is None:
            Cache._shared_arrive = Registry.getItemState("pOther_Presence_Arrive_State").intValue()
        return Cache._shared_arrive

    @staticmethod
    def setPossibleArrive(state):
        Cache._shared_possible_arriving = state

    @staticmethod
    def isPossibleArriving():
        return Cache._shared_possible_arriving

    @staticmethod
    def getLock():
        return Cache._shared_lock


@rule(
    triggers = [
        # arrive
        ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state=scope.OPEN),
        ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Streedside_State",state=scope.OPEN),

        # leave
        ItemStateChangeTrigger("pGF_Corridor_Lock_State",state=1), # door locked
        ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Streedside_State",state=scope.CLOSED)
    ]
)
class DoorCheck:
    def __init__(self):
        self.timer = None

    @staticmethod
    def isAllClosedAndLocked():
        # garage door is open
        if Registry.getItemState("pGF_Garage_Openingcontact_Door_Streedside_State") == scope.OPEN:
            return False

        # front door is not locked
        if Registry.getItemState("pGF_Corridor_Lock_State").intValue() != 1:
            return False

        return True

    def _checkArrival(self, input):
        if input['event'].getItemName() == "pGF_Corridor_Openingcontact_Door_State":
            Cache.setPossibleArrive(True)

        if Cache.getPresenceState() == PresenceHelper.STATE_AWAY:
            Cache.setPresenceState(PresenceHelper.STATE_MAYBE_PRESENT)

    def _checkLeaving(self, input = None):
        if Cache.getPresenceState() != PresenceHelper.STATE_MAYBE_PRESENT:
            return

        if not DoorCheck.isAllClosedAndLocked():
            return

        if input is None:
            Cache.setPresenceState(PresenceHelper.STATE_AWAY)
        else:
            # Lets wait for 60 seconds if another event happens, like front or garage door opened
            # 1. 'leaving' was triggered by closing garage door.
            # 1. 'leaving' was triggered by door lock event.
            self.timer = Timer.createTimeout(60, self._checkLeaving)

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        with Cache.getLock():
            if input['event'].getItemName() in ["pGF_Corridor_Openingcontact_Door_State", "pGF_Garage_Openingcontact_Door_Streedside_State"] and input['event'].getItemState() == scope.OPEN:
                self._checkArrival(input)
            else:
                self._checkLeaving(input['event'].getItemName())

@rule(
    triggers = [
        GroupStateChangeTrigger("gSensor_Indoor")
    ]
)
class MovingCheck:
    def __init__(self):
        self.timer = None

    def checkSleeping(self):
        with Cache.getLock():
            if Cache.getPresenceState() != PresenceHelper.STATE_MAYBE_SLEEPING:
                self.timer = None
                return

            if Registry.getItemState("gIndoor_Lights") == scope.ON:
                self.timer = Timer.createTimeout(60, self.checkSleeping)
            else:
                last_update_diff = ( datetime.now().astimezone() - Registry.getItem("gIndoor_Lights").getLastStateUpdate() ).total_seconds()
                if last_update_diff >= 600:
                    Cache.setPresenceState(PresenceHelper.STATE_SLEEPING)
                    self.timer = None
                else:
                    self.timer = Timer.createTimeout(60, self.checkSleeping)

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        with Cache.getLock():
            if Cache.isPossibleArriving():
                Cache.setArriving(True)

            if Cache.getPresenceState() == PresenceHelper.STATE_SLEEPING:
                Cache.setPresenceState(PresenceHelper.STATE_MAYBE_SLEEPING)

                # must be decoupled, to release lock
                self.timer = Timer.createTimeout(1, self.checkSleeping)

@rule(
    triggers = [
        GroupStateChangeTrigger("gOther_Presence_State_Raw")
    ]
)
class KnownPersonCheck:
    def __init__(self):
        self.skippedTimer = {}

    #def test(self):
    #    Registry.getItem("pOther_Presence_Sandra_State_Raw").postUpdate(scope.ON)
    #    #self.process("pOther_Presence_Sandra_State_Raw", "pOther_Presence_Sandra_State", scope.OFF)

    def process(self, item_name, related_item_name, item_state):
        with Cache.getLock():
            Registry.getItem(related_item_name).postUpdate(item_state) # Item name without raw, is the real one

            presence_state = Cache.getPresenceState()

            if item_state == scope.ON:
                # only possible if we are away
                if presence_state in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                    Cache.setPresenceState(PresenceHelper.STATE_PRESENT)
            else:
                # we must check child items instead of group item, because group item is updated too late
                if presence_state == PresenceHelper.STATE_PRESENT and len(ToolboxHelper.getFilteredGroupMember("gOther_Presence_State_Raw", scope.ON)) == 0:
                    Cache.setPresenceState(PresenceHelper.STATE_AWAY if DoorCheck.isAllClosedAndLocked() else PresenceHelper.STATE_MAYBE_PRESENT)

    def execute(self, module, input):
        item_name = input['event'].getItemName()
        related_item_name = item_name[:-4]

        new_item_state = input['event'].getItemState()
        old_item_state = input['oldState']

        item_has_skip_timer = ( item_name in self.skippedTimer )
        if item_has_skip_timer:
            self.skippedTimer[item_name].cancel()
            del self.skippedTimer[item_name]

        # sometimes, phones are losing wifi connections because of their sleep mode
        if new_item_state == scope.OFF:
            if old_item_state == scope.ON:
                if Registry.getItem("pGF_Corridor_Openingcontact_Door_State").getLastStateChange() < datetime.now().astimezone() - timedelta(minutes=60) and Cache.getArriving() > 0:
                    # relatedItem state is still ON
                    #lastChangedState = getItemLastChange(related_item_name)
                    #if itemLastChangeNewerThen("pGF_Corridor_Openingcontact_Door_State",lastChangedState.minusMinutes(15)):
                    self.skippedTimer[item_name] = Timer.createTimeout(7200, self.process, args = [ item_name, related_item_name, new_item_state ]) # 1 hour
                    NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, "System", "Delayed presence processing {} for {}".format(new_item_state,item_name))
                    return
        else:
            if old_item_state == scope.OFF and item_has_skip_timer:
                NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, "System", "Cancel presence processing {} for {}".format(new_item_state,item_name))
                return

        self.process(item_name, related_item_name, new_item_state)
          
    
@rule(
    triggers = [
        #ItemStateChangeTrigger("pGF_Corridor_Motiondetector_State",state=scope.OPEN),
        #ItemStateChangeTrigger("pGF_Livingroom_Motiondetector_State",state=scope.OPEN),
        #ItemStateChangeTrigger("pFF_Corridor_Motiondetector_State",state=scope.OPEN),
        ItemStateChangeTrigger("gGF_Lights",state=scope.ON),
        ItemStateChangeTrigger("gGF_Shutters",state=scope.UP),
        ItemStateChangeTrigger("gGF_Shutters",state="0")
    ]
)
class Wakeup:
    def __init__(self):
        self.timer = None

    def wakeup(self):
        Cache.setPresenceState(PresenceHelper.STATE_PRESENT)
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "System", "Guten Morgen")

    def delayedWakeup(self, checkCounter ):
        if Registry.getItemState("gGF_Lights") == scope.ON:
            with Cache.getLock():
                if Cache.getPresenceState() in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                    lightCount = 0
                    for child in Registry.getItem("gGF_Lights").getAllMembers():
                        if child.getStateAs(scope.OnOffType) == scope.ON:
                            lightCount = lightCount + 1
                    # Signs (in first floor) for wake up are
                    # - a light is ON for more then 10 minutes
                    # - or more then 2 lights in total are ON
                    if checkCounter == 20 or lightCount > 2:
                        self.wakeup()
                        self.timer = None
                    else:
                        self.timer = Timer.createTimeout(30, self.delayedWakeup, args = [ checkCounter + 1 ])
        else:
            self.timer = None
        
    def execute(self, module, input):        
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        with Cache.getLock():
            if Cache.getPresenceState() in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                # sometimes the "gGF_Lights" state switches back and forth for a couple of milliseconds when set "gGF_Lights" state to OFF
                if input['event'].getItemName() == "gGF_Shutters":
                    self.wakeup()
                else:
                    self.timer = Timer.createTimeout(30, self.delayedWakeup, args = [ 0 ])


@rule(
    triggers = [
        ItemCommandTrigger("pOther_Scene4",command=scope.ON)
    ]
)
class Sleeping:
    def execute(self, module, input):
        with Cache.getLock():
            if Cache.getPresenceState() in [PresenceHelper.STATE_MAYBE_PRESENT,PresenceHelper.STATE_PRESENT,PresenceHelper.STATE_MAYBE_SLEEPING]:
                Cache.setPresenceState(PresenceHelper.STATE_SLEEPING)
