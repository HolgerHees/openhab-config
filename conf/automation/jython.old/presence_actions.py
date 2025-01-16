from java.time import ZonedDateTime
import time

from shared.helper import rule, getItemState, getFilteredChildItems, getItemLastUpdate, startTimer, sendCommand, sendCommandIfChanged, getGroupMember, getGroupMemberChangeTrigger, NotificationHelper, UserHelper
from shared.triggers import ItemStateChangeTrigger
from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper
from custom.shuffle import ShuffleHelper


@rule()
class PresenceActionUnknownPerson:
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
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_WARN, u"System", u"Unbekannter Gast {}".format(u"gegangen" ), "https://smartmarvin.de/cameraStreedsideImage")

        elif newPresentState == PresenceHelper.STATE_MAYBE_PRESENT:
            if oldPresentState == PresenceHelper.STATE_AWAY:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_WARN, u"System", u"Unbekannter Gast gekommen", "https://smartmarvin.de/cameraStreedsideImage")

        elif newPresentState == PresenceHelper.STATE_PRESENT:
            if oldPresentState == PresenceHelper.STATE_MAYBE_PRESENT:
                # lastChange Date is comming from database which can be updated too late
                # thats why I add a async task with a delay of 2 seconds here
                self.timer = startTimer(self.log, 2, self.checkArriving, args = [] )

@rule()
class PresenceActionKnownPerson:
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

@rule()
class PresenceActionAlexaWelcome:
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

            # already confirmed
            if not last_change.isAfter(self.arrivedUser[user_name]):
                continue

            if confirm:
                self.arrivedUser[user_name] = last_change

            # person arrived more then 30 minutes ago, we can ignore welcome
            if last_change.plusMinutes(30).isBefore(ZonedDateTime.now()):
                continue

            arrived_user.append(UserHelper.getName(user_name))
        return arrived_user

    def isNewGuestArrived(self, confirm):
        state = getItemState("pOther_Presence_State").intValue()
        if state == PresenceHelper.STATE_MAYBE_PRESENT:
            lastUpdate = getItemLastUpdate("pOther_Presence_State")
            if not lastUpdate.isAfter(self.guestUser):
                return False
            if confirm:
                self.guestUser = lastUpdate
            return True

    def checkArriving(self):
        arrived_user = self.getArrivedUser(True)
        if len(arrived_user) > 0:
            welcome_msg = ShuffleHelper.getRandomSynonym(self.log, u"Willkommen zu Hause", len(arrived_user) > 1)
            AlexaHelper.sendTTS(u"Hallo {}, {}".format(" und Hallo ".join(arrived_user), welcome_msg), location = "lGF_Corridor")
        elif self.isNewGuestArrived(True):
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

@rule()
class PresenceActionArrivingAction:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state="OPEN") ]

    def execute(self, module, input):
        if getItemState("pOther_Automatic_State_Outdoorlights") != ON:
            return

        # no outside motion detector event in the last 60 seconds
        if getItemLastUpdate("pOutdoor_Streedside_Frontdoor_Motiondetector_State").plusSeconds(60).isBefore(ZonedDateTime.now()):
            return

        # light was already switched on/off during the last 30 seconds
        if getItemLastUpdate("pGF_Corridor_Light_Ceiling_Powered").plusSeconds(30).isAfter(ZonedDateTime.now()):
            return

        sendCommandIfChanged("pGF_Corridor_Light_Ceiling_Powered",ON)

@rule()
class PresenceActionLeavingAction:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State", state=PresenceHelper.STATE_AWAY)]

    def execute(self, module, input):
        if input["oldState"].intValue() == PresenceHelper.STATE_MAYBE_PRESENT:
            if getItemState("pOther_Automatic_State_Outdoorlights") == ON:
                sendCommandIfChanged("pGF_Corridor_Light_Ceiling_Powered",OFF)

@rule()
class PresenceActionSleepingAction:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State",state=PresenceHelper.STATE_SLEEPING)]
            
    def execute(self, module, input):
        sendCommandIfChanged("gIndoor_Lights", OFF)
        sendCommandIfChanged("gOutdoor_Terrace_Light_Hue_Color", OFF)
        sendCommandIfChanged("pOutdoor_Light_Automatic_Main_Switch", ON)

        if getItemState("pGF_Corridor_Lock_State").intValue() != 1:
            sendCommand("pGF_Corridor_Lock_Action", 2)
        
        #sendCommandIfChanged("pGF_Livingroom_Socket_Couch_Powered", OFF)
        #sendCommandIfChanged("pGF_Livingroom_Socket_Fireplace_Powered", OFF)

        #for child in getGroupMember("gAll_Sockets"):
        #    if child.getName() in ["pFF_Attic_Socket_Powered","pMobile_Socket_6_Powered"]:
        #        continue
        #    sendCommandIfChanged(child, OFF)

