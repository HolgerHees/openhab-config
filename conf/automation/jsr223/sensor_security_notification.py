from java.time import ZonedDateTime

from shared.helper import rule, isMember, getGroupMemberChangeTrigger, getItem, getItemState, NotificationHelper
from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper


@rule()
class SensorSecurityNotificationAwayAlerts:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gOpeningcontacts")
        self.triggers += getGroupMemberChangeTrigger("gSensor_Indoor")

        self.last_notification = ZonedDateTime.now()

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Security_Notify") != ON:
            return

        state = getItemState("pOther_Presence_State").intValue()
        if state != PresenceHelper.STATE_AWAY:
            return

        itemName = input['event'].getItemName()

        # Other main door events are handled inside presence detection.
        if itemName in ["pGF_Corridor_Openingcontact_Door_State","pGF_Garage_Openingcontact_Door_Streedside_State"]:
            return

        item = getItem(itemName)
        isOpen = input['event'].getItemState()

        if "pToolshed_Openingcontact_Door_State" == itemName:
            msg = u"Tür der Gartenlaube {}".format( u"offen" if isOpen else u"geschlossen" )
        elif "pToolshed_Openingcontact_Window_State" == itemName:
            msg = u"Fenster der Gartenlaube {}".format( u"offen" if isOpen else u"geschlossen" )
        elif "pGF_Garage_Openingcontact_Door_Garden_State" == itemName:
            msg = u"Garagentür zum Garten {}".format( u"offen" if isOpen else u"geschlossen" )
        elif isMember(itemName, "gGF_Sensor_Window"):
            msg = u"Fenster im Ergeschoss {}".format( u"offen" if isOpen else u"geschlossen" )
        elif isMember(itemName, "gFF_Sensor_Window"):
            msg = u"Fenster im Obergeschoss {}".format( u"offen" if isOpen else u"geschlossen" )
        elif isMember(itemName, "gSensor_Indoor"):
            if not isOpen:
                return
            if itemName == "pGF_Corridor_Motiondetector_State":
                msg = u"Bewegung im Flur unten erkannt"
            elif itemName == "pFF_Corridor_Motiondetector_State":
                msg = u"Bewegung im Flur oben erkannt"
            elif itemName == "pGF_Livingroom_Motiondetector_State":
                msg = u"Bewegung im Wohnzimmer erkannt"
            else:
                msg = u"Unbekannter Motions detector {}".format(itemName)
        else:
            self.log.info(u"Unerwartes Item Event {} {}".format(itemName, u"offen" if isOpen else u"geschlossen"))

        now = ZonedDateTime.now()
        if ChronoUnit.MINUTES.between(self.last_notification, now) > 5:
            if "Motiondetector" in itemName:
                NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_ALERT, u"Alarm", u"{}".format(msg))
            else:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, u"Alarm", u"{}".format(msg))
            self.last_notification = now

@rule()
class SensorSecurityNotificationSleepAlerts:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gOpeningcontacts", "OPEN")

    def execute(self, module, input):
        state = getItemState("pOther_Presence_State").intValue()
        if state != PresenceHelper.STATE_SLEEPING:
            return

        if isMember(input['event'].getItemName(), "gGF_Sensor_Doors"):
            msg = u"Die Haustür wurde unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
        elif isMember(input['event'].getItemName(), "gGF_Sensor_Window"):
            msg = u"Es wurde ein Fenster im Ergeschoss unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
        elif isMember(input['event'].getItemName(), "gFF_Sensor_Window"):
            msg = u"Es wurde ein Fenster im Obergeschoss unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", effects = AlexaHelper.EFFECT_WISPER)

        elif input['event'].getItemName() == "pToolshed_Openingcontact_Door_State":
            msg = u"Es wurde die Tür des Geräteschuppens unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
        elif input['event'].getItemName() == "pToolshed_Openingcontact_Window_State":
            msg = u"Es wurde das Fenster des Geräteschuppens unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
        else:
            msg = u"Unbekannter Fenster oder Tür Kontakt unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
            self.log.error(msg)

        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Alarm", msg)
