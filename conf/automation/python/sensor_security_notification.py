from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper
from shared.notification import NotificationHelper

from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper

from datetime import datetime


@rule()
class AwayAlerts:
    def __init__(self):
        self.last_notification = datetime.now().astimezone()

    def buildTriggers(self):
        triggers = []
        triggers += ToolboxHelper.getGroupMemberTrigger(ItemStateChangeTrigger, "gOpeningcontacts")
        triggers += ToolboxHelper.getGroupMemberTrigger(ItemStateChangeTrigger, "gSensor_Indoor")
        return triggers

    def execute(self, module, input):
        if Registry.getItemState("pOther_Manual_State_Security_Notify") != ON:
            return

        state = Registry.getItemState("pOther_Presence_State").intValue()
        if state != PresenceHelper.STATE_AWAY:
            return

        item_name = input['event'].getItemName()

        # Other main door events are handled inside presence detection.
        if item_name in ["pGF_Corridor_Openingcontact_Door_State","pGF_Garage_Openingcontact_Door_Streedside_State"]:
            return

        item = Registry.getItem(item_name)
        isOpen = input['event'].getItemState()

        if "pToolshed_Openingcontact_Door_State" == item_name:
            msg = "Tür der Gartenlaube {}".format( "offen" if isOpen else "geschlossen" )
        elif "pToolshed_Openingcontact_Window_State" == item_name:
            msg = "Fenster der Gartenlaube {}".format( "offen" if isOpen else "geschlossen" )
        elif "pGF_Garage_Openingcontact_Door_Garden_State" == item_name:
            msg = "Garagentür zum Garten {}".format( "offen" if isOpen else "geschlossen" )
        elif ToolboxHelper.isMember(item_name, "gGF_Sensor_Window"):
            msg = "Fenster im Ergeschoss {}".format( "offen" if isOpen else "geschlossen" )
        elif ToolboxHelper.isMember(item_name, "gFF_Sensor_Window"):
            msg = "Fenster im Obergeschoss {}".format( "offen" if isOpen else "geschlossen" )
        elif ToolboxHelper.isMember(item_name, "gSensor_Indoor"):
            if not isOpen:
                return
            if item_name == "pGF_Corridor_Motiondetector_State":
                msg = "Bewegung im Flur unten erkannt"
            elif item_name == "pFF_Corridor_Motiondetector_State":
                msg = "Bewegung im Flur oben erkannt"
            elif item_name == "pGF_Livingroom_Motiondetector_State":
                msg = "Bewegung im Wohnzimmer erkannt"
            else:
                msg = "Unbekannter Motions detector {}".format(item_name)
        else:
            self.logger.info("Unerwartes Item Event {} {}".format(item_name, "offen" if isOpen else "geschlossen"))

        now = datetime.now().astimezone()
        if int((self.last_notification - now).total_seconds() / 60) > 5:
            if "Motiondetector" in item_name:
                NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_ALERT, "Alarm", "{}".format(msg))
            else:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, "Alarm", "{}".format(msg))
            self.last_notification = now

@rule()
class SleepAlerts:
    def buildTriggers(self):
        triggers = []
        triggers += ToolboxHelper.getGroupMemberTrigger(ItemStateChangeTrigger, "gOpeningcontacts", "OPEN")
        return triggers

    def execute(self, module, input):
        state = Registry.getItemState("pOther_Presence_State").intValue()
        if state != PresenceHelper.STATE_SLEEPING:
            return

        if ToolboxHelper.isMember(input['event'].getItemName(), "gGF_Sensor_Doors"):
            msg = "Die Haustür wurde unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
        elif ToolboxHelper.isMember(input['event'].getItemName(), "gGF_Sensor_Window"):
            msg = "Es wurde ein Fenster im Ergeschoss unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
        elif ToolboxHelper.isMember(input['event'].getItemName(), "gFF_Sensor_Window"):
            msg = "Es wurde ein Fenster im Obergeschoss unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", effects = AlexaHelper.EFFECT_WISPER)

        elif input['event'].getItemName() == "pToolshed_Openingcontact_Door_State":
            msg = "Es wurde die Tür des Geräteschuppens unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
        elif input['event'].getItemName() == "pToolshed_Openingcontact_Window_State":
            msg = "Es wurde das Fenster des Geräteschuppens unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
        else:
            msg = "Unbekannter Fenster oder Tür Kontakt unerwartet geöffnet"
            AlexaHelper.sendTTS(msg, location = "lFF_Bedroom", priority = NotificationHelper.PRIORITY_ALERT)
            self.logger.error(msg)

        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Alarm", msg)
