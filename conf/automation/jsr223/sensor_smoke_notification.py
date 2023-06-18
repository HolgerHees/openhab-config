from shared.helper import rule, ItemStateChangeTrigger, NotificationHelper
from custom.alexa import AlexaHelper


@rule("scene_contact_notifications.py")
class SmokeDetectorNotificationsRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Smoke_Detector_State",state="OPEN")]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, "Alarm", u"Rauchmelder")

        AlexaHelper.sendAlarmTTSToLocation("lFF_Bedroom", "Achtung, es brennt")
        AlexaHelper.sendAlarmTTSToLocation("lGF_Livingroom", "Achtung, es brennt")
