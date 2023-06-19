import urllib2
from java.time import ZonedDateTime

from shared.helper import rule, getItemState, itemLastChangeOlderThen, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged, getGroupMember, getGroupMemberChangeTrigger, NotificationHelper, UserHelper
from shared.triggers import ItemStateChangeTrigger

from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper

import time

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
                for user_name in UserHelper.getPresentUser(timeout = 10):
                    user_fullnames.append(UserHelper.getName(user_name))

                if len(user_fullnames) == 1:
                    NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"System", u"Unbekannter Gast ist {}".format( user_fullnames[0] ) )
                elif len(user_fullnames) > 1:
                    NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"System", u"Unbekannte Gaest sind {}".format( " und ".join(user_fullnames) ) )
                else:
                    self.log.error("Unbekannte Gäste konnten nicht bestimmt werden")

@rule("presence_actions.py")
class KnownPersonRuleRule:
    def __init__(self):
        self.triggers = getGroupMemberChangeTrigger("gOther_Presence_State")

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        itemState = input['event'].getItemState()

        userName = UserHelper.getUserByStateItem(itemName)

        if itemState == OFF:
            if getItemState("gOther_Presence_State") == OFF:
                lightMsg = u" - LICHT an" if getItemState("gIndoor_Lights") != OFF else u""
                windowMsg = u" - FENSTER offen" if getItemState("gOpeningcontacts") != CLOSED else u""
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"System", u"Auf Wiedersehen{}{}".format(lightMsg,windowMsg), recipients = [userName])
            else:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"System", u"Auf Wiedersehen", recipients = [userName])
        else:
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"System", u"Willkommen", recipients = [userName])

@rule("presence_actions.py")
class ArrivingActionRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State"),
            ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State",state="OPEN")
        ]

    def execute(self, module, input):
        if input["event"].getItemName() == "pGF_Corridor_Openingcontact_Door_State":
            if itemLastChangeOlderThen("pGF_Corridor_Motiondetector_State", ZonedDateTime.now().minusMinutes(10)):

                user_fullnames = []
                for user_name in UserHelper.getPresentUser(timeout = 10):
                    user_fullnames.append(UserHelper.getName(user_name))

                if len(user_fullnames) > 0:
                    AlexaHelper.sendTTS("Hallo {}, Willkommen zu Hause".format(" und Hallo ".join(user_fullnames)), location = "lGF_Corridor")
                else:
                    AlexaHelper.sendTTS("Willkommen zu Hause", location = "lGF_Corridor")

                if getItemState("pOther_Automatic_State_Outdoorlights") == ON:
                    sendCommandIfChanged("pGF_Corridor_Light_Ceiling_Powered",ON)
        elif input["event"].getItemState().intValue() == PresenceHelper.STATE_AWAY and input["oldState"].intValue() == PresenceHelper.STATE_MAYBE_PRESENT:
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
    
