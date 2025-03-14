from openhab import rule, Registry, Timer
from openhab.triggers import ItemStateChangeTrigger, GroupStateChangeTrigger

from shared.notification import NotificationHelper
from shared.user import UserHelper
from shared.toolbox import ToolboxHelper

from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper
from custom.shuffle import ShuffleHelper

from custom.frigate import FrigateHelper

from datetime import datetime, timedelta
import time

import scope






@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Presence_State")
    ]
)
class UnknownPerson:
    def __init__(self):
        self.timer = None

    def checkArriving(self):
        user_fullnames = []
        ref = datetime.now().astimezone() - timedelta(seconds=5)
        for user_name, stateItem in UserHelper.getPresentUserData().items():
            if ToolboxHelper.getLastUpdate(stateItem) < ref:
                continue
            user_fullnames.append(UserHelper.getName(user_name))

        if len(user_fullnames) == 1:
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "System", "Unbekannter Gast ist {}".format( user_fullnames[0] ) )
        elif len(user_fullnames) > 1:
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "System", "Unbekannte Gaest sind {}".format( " und ".join(user_fullnames) ) )
        else:
            self.logger.error("Not able to detect unknown guests")

        self.timer = None

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        new_presence_state = input["event"].getItemState().intValue()
        old_presence_state = input["oldState"].intValue()

        if new_presence_state == PresenceHelper.STATE_AWAY:
            if old_presence_state == PresenceHelper.STATE_MAYBE_PRESENT:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_WARN, "System", "Unbekannter Gast {}".format("gegangen" ), FrigateHelper.getLatestSnapshotUrl("streedside"))

        elif new_presence_state == PresenceHelper.STATE_MAYBE_PRESENT:
            if old_presence_state == PresenceHelper.STATE_AWAY:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_WARN, "System", "Unbekannter Gast gekommen", FrigateHelper.getLatestSnapshotUrl("streedside"))

        elif new_presence_state == PresenceHelper.STATE_PRESENT:
            if old_presence_state == PresenceHelper.STATE_MAYBE_PRESENT:
                # lastChange Date is comming from database which can be updated too late
                # thats why I add a async task with a delay of 2 seconds here
                self.timer = Timer.createTimeout( 2, self.checkArriving, args = [] )

@rule(
    triggers = [
        GroupStateChangeTrigger("gOther_Presence_State")
    ]
)
class KnownPerson:
    def execute(self, module, input):
        item_name = input['event'].getItemName()
        item_state = input['event'].getItemState()

        user_name = UserHelper.getUserByStateItem(item_name)

        if item_state == scope.OFF:
            # we must check child items instead of group item, because group item is updated too late
            if len(ToolboxHelper.getFilteredGroupMember("gOther_Presence_State", scope.ON)) == 0:
                lightMsg = " - LICHT an" if Registry.getItemState("gIndoor_Lights") != scope.OFF else ""
                windowMsg = " - FENSTER offen" if Registry.getItemState("gOpeningcontactsSecurityRelevant") != scope.CLOSED else ""
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "System", "Auf Wiedersehen{}{}".format(lightMsg,windowMsg), recipients = [user_name])
            else:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "System", "Auf Wiedersehen", recipients = [user_name])
        else:
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "System", "Willkommen", recipients = [user_name])

@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Presence_Arrive_State")
    ]
)
class AlexaWelcome:
    def __init__(self):
        self.timer = None

        self.guest_user = datetime.now().astimezone()
        self.arrived_user = {}
        for user_name in UserHelper.getUserNames():
            self.arrived_user[user_name] = datetime.now().astimezone()

    def getArrivedUser(self, arrived_state_count):
        arrived_user = []
        for user_name, stateItem in UserHelper.getPresentUserData().items():
            last_change = ToolboxHelper.getLastUpdate(stateItem)

            # already confirmed
            if last_change <= self.arrived_user[user_name]:
                continue

            self.arrived_user[user_name] = last_change

            # if already has a person arrived and the next detected person arrived more then 5 minutes ago, we can ignore welcome
            if arrived_state_count > 1 and last_change + timedelta(minutes=5) < datetime.now().astimezone():
                continue

            arrived_user.append(UserHelper.getName(user_name))
        return arrived_user

    def isNewGuestArrived(self):
        state = Registry.getItemState("pOther_Presence_State").intValue()
        if state == PresenceHelper.STATE_MAYBE_PRESENT:
            last_update = ToolboxHelper.getLastUpdate("pOther_Presence_State")
            if last_update <= self.guest_user:
                return False
            self.guest_user = last_update
            return True

    def checkArriving(self, arrived_state_count):
        arrived_user = self.getArrivedUser(arrived_state_count)
        if len(arrived_user) > 0:
            welcome_msg = ShuffleHelper.getRandomSynonym("Willkommen zu Hause", len(arrived_user) > 1)
            AlexaHelper.sendTTS("Hallo {}, {}".format(" und Hallo ".join(arrived_user), welcome_msg), location = "lGF_Corridor")
        elif self.isNewGuestArrived():
            AlexaHelper.sendTTS("Hallo, unbekannter Gast. Die Hausbewohner wurden über Ihre Ankunft benachrichtigt.", location = "lGF_Corridor")

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        arrived_state_count = input['event'].getItemState().intValue()
        if arrived_state_count > 0:
            self.checkArriving(arrived_state_count)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state=scope.OPEN)
    ]
)
class ArrivingAction:
    def execute(self, module, input):
        if Registry.getItemState("pOther_Automatic_State_Outdoorlights") != scope.ON:
            return

        # no outside motion detector event in the last 60 seconds
        if ToolboxHelper.getLastUpdate("pOutdoor_Streedside_Frontdoor_Motiondetector_State") + timedelta(seconds=60) < datetime.now().astimezone():
            return

        # light was already switched on/off during the last 30 seconds
        if ToolboxHelper.getLastUpdate("pGF_Corridor_Light_Ceiling_Powered") + timedelta(seconds=30) > datetime.now().astimezone():
            return

        Registry.getItem("pGF_Corridor_Light_Ceiling_Powered").sendCommandIfDifferent(scope.ON)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Presence_State", state=PresenceHelper.STATE_AWAY)
    ]
)
class LeavingAction:
    def execute(self, module, input):
        if input["oldState"].intValue() == PresenceHelper.STATE_MAYBE_PRESENT:
            if Registry.getItemState("pOther_Automatic_State_Outdoorlights") == scope.ON:
                Registry.getItem("pGF_Corridor_Light_Ceiling_Powered").sendCommandIfDifferent(scope.OFF)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Presence_State",state=PresenceHelper.STATE_SLEEPING)
    ]
)
class SleepingAction:
    def execute(self, module, input):
        Registry.getItem("gIndoor_Lights").sendCommandIfDifferent(scope.OFF)
        Registry.getItem("gOutdoor_Terrace_Light_Hue_Color").sendCommandIfDifferent(scope.OFF)
        Registry.getItem("pOutdoor_Light_Automatic_Main_Switch").sendCommandIfDifferent(scope.ON)

        if Registry.getItemState("pGF_Corridor_Lock_State").intValue() != 1:
            Registry.getItem("pGF_Corridor_Lock_Action").sendCommand(2)
        
        #Registry.getItem("pGF_Livingroom_Socket_Couch_Powered").sendCommandIfDifferent(scope.OFF)
        #Registry.getItem("pGF_Livingroom_Socket_Fireplace_Powered").sendCommandIfDifferent(scope.OFF)

        #for child in Registry.getItem("gAll_Sockets").getAllMembers():
        #    if child.getName() in ["pFF_Attic_Socket_Powered","pMobile_Socket_6_Powered"]:
        #        continue
        #    Registry.getItem(child).sendCommandIfDifferent(scope.OFF)

