import urllib2
from java.time import ZonedDateTime
import time

from shared.helper import rule, getItemState, getFilteredChildItems, getItemLastUpdate, itemLastChangeOlderThen, postUpdate, postUpdateIfChanged, startTimer, sendCommand, sendCommandIfChanged, getGroupMember, getGroupMemberChangeTrigger, NotificationHelper, UserHelper
from shared.triggers import ItemStateChangeTrigger

from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper
from custom.shuffle import ShuffleHelper


@rule("presence_actions.py")
class UnknownPersonRuleRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State")]

        self.timer = None

    def checkArriving(self):
        user_fullnames = []
        ref = ZonedDateTime.now().minusSeconds(5)
        for user_name, stateItem in UserHelper.getPresentUserData().items():
            _update = getItemLastUpdate(stateItem)
            if _update.isBefore(ref):
                continue
            user_fullnames.append(UserHelper.getName(user_name))

        if len(user_fullnames) == 1:
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"System", u"Unbekannter Gast ist {}".format( user_fullnames[0] ) )
        elif len(user_fullnames) > 1:
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"System", u"Unbekannte Gaest sind {}".format( " und ".join(user_fullnames) ) )
        else:
            self.log.error(u"Not able to detect unknown guests")

        self.timer = None

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        newPresentState = input["event"].getItemState().intValue()
        oldPresentState = input["oldState"].intValue()

        if newPresentState == PresenceHelper.STATE_AWAY:
            if oldPresentState == PresenceHelper.STATE_MAYBE_PRESENT:
                isFallback = False # => 1 hour of no moving in the house
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_WARN, u"System", u"Unbekannter Gast {}".format( u"verschwunden" if isFallback else u"gegangen" ), "https://smartmarvin.de/cameraStrasseImage")

        elif newPresentState == PresenceHelper.STATE_MAYBE_PRESENT:
            if oldPresentState == PresenceHelper.STATE_AWAY:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_WARN, u"System", u"Unbekannter Gast gekommen", "https://smartmarvin.de/cameraStrasseImage")

        elif newPresentState == PresenceHelper.STATE_PRESENT:
            if oldPresentState == PresenceHelper.STATE_MAYBE_PRESENT:
                # lastChange Date is comming from database which can be updated too late
                # thats why I add a async task with a delay of 2 seconds here
                self.timer = startTimer(self.log, 2, self.checkArriving, args = [ZonedDateTime.now()] )

@rule("presence_actions.py")
class KnownPersonRuleRule:
    def __init__(self):
        self.triggers = getGroupMemberChangeTrigger("gOther_Presence_State")

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        itemState = input['event'].getItemState()

        userName = UserHelper.getUserByStateItem(itemName)

        if itemState == OFF:
            # we must check child items instead of group item, because group item is updated too late
            if len(getFilteredChildItems("gOther_Presence_State", ON)) == 0:
                lightMsg = u" - LICHT an" if getItemState("gIndoor_Lights") != OFF else u""
                windowMsg = u" - FENSTER offen" if getItemState("gOpeningcontactsSecurityRelevant") != CLOSED else u""
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"System", u"Auf Wiedersehen{}{}".format(lightMsg,windowMsg), recipients = [userName])
            else:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"System", u"Auf Wiedersehen", recipients = [userName])
        else:
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"System", u"Willkommen", recipients = [userName])

@rule("presence_actions.py")
class AlexaWelcomeRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOther_Presence_Arrive_State") ]

        self.timer = None

        self.guestUser = ZonedDateTime.now()
        self.arrivedUser = {}
        for user_name in UserHelper.getUserNames():
            self.arrivedUser[user_name] = ZonedDateTime.now()

    def getArrivedUser(self, confirm):
        arrived_user = []
        for user_name, stateItem in UserHelper.getPresentUserData().items():
            last_change = getItemLastUpdate(stateItem)
            if last_change.isBefore(self.arrivedUser[user_name]):
                continue
            if confirm:
                self.arrivedUser[user_name] = last_change
            arrived_user.append(UserHelper.getName(user_name))
        return arrived_user

    def isNewGuestArrived(self):
        state = getItemState("pOther_Presence_State").intValue()
        if state == PresenceHelper.STATE_MAYBE_PRESENT:
            lastUpdate = getItemLastUpdate("pOther_Presence_State")
            if self.guestUser.isBefore(lastUpdate):
                self.guestUser = lastUpdate
                return True
        return False

    def checkArriving(self):
        arrived_user = self.getArrivedUser(True)
        if len(arrived_user) > 0:
            welcome_msg = ShuffleHelper.getRandomSynonym(u"Willkommen zu Hause")
            AlexaHelper.sendTTS(u"Hallo {}, {}".format(" und Hallo ".join(arrived_user), welcome_msg), location = "lGF_Corridor")
        elif self.isNewGuestArrived():
            AlexaHelper.sendTTS(u"Hallo, unbekannter Gast. Die Hausbewohner wurden über Ihre Ankunft benachrichtigt.", location = "lGF_Corridor")

        if len(UserHelper.getPresentUser()) != len(self.arrivedUser):
            # confirm late arrived user
            self.timer = startTimer(self.log, 300, self.confirmArrivedUser )
        else:
            self.timer = None

    def confirmArrivedUser(self):
        self.getArrivedUser(True)
        self.timer = None

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        if input['event'].getItemState().intValue() > 0:
            self.checkArriving()

@rule("presence_actions.py")
class ArrivingActionRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state="OPEN") ]

    def execute(self, module, input):
        if getItemState("pOther_Automatic_State_Outdoorlights") != ON:
            return

        _update = getItemLastUpdate("pOutdoor_Streedside_Frontdoor_Motiondetector_State")
        # switch light on if outdoor motion detector was triggered directly before
        if _update.plusSeconds(10).isAfter(ZonedDateTime.now()):
            sendCommandIfChanged("pGF_Corridor_Light_Ceiling_Powered",ON)

@rule("presence_actions.py")
class LeavingActionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State", PresenceHelper.STATE_AWAY)]

    def execute(self, module, input):
        if input["oldState"].intValue() == PresenceHelper.STATE_MAYBE_PRESENT:
            if getItemState("pOther_Automatic_State_Outdoorlights") == ON:
                sendCommandIfChanged("pGF_Corridor_Light_Ceiling_Powered",OFF)

@rule("presence_actions.py")
class SleepingActionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State",state=PresenceHelper.STATE_SLEEPING)]
            
    def execute(self, module, input):
        sendCommandIfChanged("gIndoor_Lights", OFF)
        sendCommandIfChanged("gOutdoor_Terrace_Light_Hue_Color", OFF)
        sendCommandIfChanged("pOutdoor_Light_Automatic_Main_Switch", ON)
        
        for child in getGroupMember("gAll_Sockets"):
            if child.getName() == "pFF_Attic_Socket_Powered":
                continue
            sendCommandIfChanged(child, OFF)

