import urllib2
from java.time import ZonedDateTime
import time

from shared.helper import rule, getItemState, getFilteredChildItems, getItemLastUpdate, itemLastChangeOlderThen, postUpdate, postUpdateIfChanged, startTimer, sendCommand, sendCommandIfChanged, getGroupMember, getGroupMemberChangeTrigger, NotificationHelper, UserHelper
from shared.triggers import ItemStateChangeTrigger

from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper
from custom.shuffle import ShuffleHelper


@rule("presence_actions.py")
class ArrivingActionRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state="OPEN") ]

        self.arrivedUser = {}
        self.arrivingTimer = None

    def checkArrivedUser(self, user_name, last_change, confirm):
        if user_name in self.arrivedUser and not last_change.isAfter(self.arrivedUser[user_name]):
            return False

        if confirm:
            self.arrivedUser[user_name] = last_change

        return True

    def getArrivedUser(self, confirm):
        arrived_user = []
        for user_name, stateItem in UserHelper.getPresentUserData().items():
            if not self.checkArrivedUser(user_name, getItemLastUpdate(stateItem), confirm):
                continue
            arrived_user.append(UserHelper.getName(user_name))
        return arrived_user

    def checkArriving(self, doorOpenTime):
        if itemLastChangeOlderThen("pGF_Corridor_Motiondetector_State", doorOpenTime):
            # check for maximum of 20 seconds
            if ZonedDateTime.now().minusSeconds(20).isBefore(doorOpenTime):
                self.arrivingTimer = startTimer(self.log, 1, self.checkArriving, args = [doorOpenTime] )
            return

        self.confirmTimer = None

        arrived_user = self.getArrivedUser(True)
        if len(arrived_user) > 0:
            welcome_msg = ShuffleHelper.getRandomSynonym(u"Willkommen zu Hause")
            AlexaHelper.sendTTS(u"Hallo {}, {}".format(" und Hallo ".join(arrived_user), welcome_msg), location = "lGF_Corridor")
        else:
            state = getItemState("pOther_Presence_State").intValue()
            if state in [PresenceHelper.STATE_AWAY, PresenceHelper.STATE_MAYBE_PRESENT]:
                if state == PresenceHelper.STATE_MAYBE_PRESENT:
                    lastUpdate = getItemLastUpdate("pOther_Presence_State")
                else:
                    # if away, a presence state change will happen during next seconds by rule "PresenceMovingCheckRule" in presence_detection.py
                    lastUpdate = ZonedDateTime.now().plusSeconds(5)
                if self.checkArrivedUser("guest", lastUpdate):
                    AlexaHelper.sendTTS(u"Hallo, unbekannter Gast. Die Hausbewohner wurden über Ihre Ankunft benachrichtigt.", location = "lGF_Corridor")

    def execute(self, module, input):
        arrived_user = self.getArrivedUser(False)
        if len(arrived_user) > 0 or itemLastChangeOlderThen("pGF_Corridor_Motiondetector_State", ZonedDateTime.now().minusMinutes(10)):

            if getItemState("pOther_Automatic_State_Outdoorlights") == ON:
                sendCommandIfChanged("pGF_Corridor_Light_Ceiling_Powered",ON)

            if self.arrivingTimer is not None:
                self.arrivingTimer.cancel()
            self.arrivingTimer = startTimer(self.log, 1, self.checkArriving, args = [ZonedDateTime.now()] )

@rule("presence_actions.py")
class LeavingActionRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOther_Presence_State", PresenceHelper.STATE_AWAY) ]

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
    
@rule("presence_actions.py")
class UnknownPersonRuleRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State")
        ]

    def execute(self, module, input):
        newPresentState = input["event"].getItemState().intValue()
        oldPresentState = input["oldState"].intValue()
        if newPresentState == PresenceHelper.STATE_AWAY:
            if oldPresentState == PresenceHelper.STATE_MAYBE_PRESENT:
                isFallback = False # => 1 hour of no moving in the house
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_WARN, u"System", u"Unbekannter Gast {}".format( u"verschwunden" if isFallback else u"gegangen" ))

        elif newPresentState == PresenceHelper.STATE_MAYBE_PRESENT:
            if oldPresentState in [PresenceHelper.STATE_AWAY, PresenceHelper.STATE_SLEEPING]:
                priority = NotificationHelper.PRIORITY_WARN if oldPresentState == PresenceHelper.STATE_AWAY else NotificationHelper.PRIORITY_ALERT
                NotificationHelper.sendNotification(priority, u"System", u"Unbekannter Gast gekommen")

        elif newPresentState == PresenceHelper.STATE_PRESENT:
            if oldPresentState == PresenceHelper.STATE_MAYBE_PRESENT:
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
                    # can happen, because lastChange Date is comming from database which can be updated too late
                    # maybe add a async task with a delay of 2 seconds here

                    stateItemRaw = getItem("pOther_Presence_Holger_State_Raw")
                    lastUpdateRaw = getItemLastUpdate(stateItemRaw)
                    self.log.info("Holgers RAW ITEM STATE: {} {}".format(getItemState(stateItemRaw), lastUpdateRaw))
                    self.log.info("Holgers RAW HISTORIC ITEM STATE: {}".format(getHistoricItemState(stateItemRaw, lastUpdateRaw)))

                    stateItem = getItem("pOther_Presence_Holger_State")
                    lastUpdate = getItemLastUpdate(stateItem)
                    self.log.info("Holgers ITEM STATE: {} {}".format(getItemState(stateItem), lastUpdate))
                    self.log.info("Holgers HISTORIC ITEM STATE: {}".format(getHistoricItemState(stateItem, lastUpdate)))

                    stateItemRaw = getItem("pOther_Presence_Sandra_State_Raw")
                    lastUpdateRaw = getItemLastUpdate(stateItemRaw)
                    self.log.info("Sandras RAW ITEM STATE: {} {}".format(getItemState(stateItemRaw), lastUpdateRaw))
                    self.log.info("Sandras RAW HISTORIC ITEM STATE: {}".format(getHistoricItemState(stateItemRaw, lastUpdateRaw)))

                    stateItem = getItem("pOther_Presence_Sandra_State")
                    lastUpdate = getItemLastUpdate(stateItem)
                    self.log.info("Sandras ITEM STATE: {} {}".format(getItemState(stateItem), lastUpdate))
                    self.log.info("Sandras HISTORIC ITEM STATE: {}".format(getHistoricItemState(stateItem, lastUpdate)))

                    self.log.error(u"Unbekannte Gäste konnten nicht bestimmt werden")

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
