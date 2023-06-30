from shared.helper import rule, ItemStateChangeTrigger, NotificationHelper
from custom.alexa import AlexaHelper


@rule()
class SensorSmokeNotification:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Smoke_Detector_State",state="OPEN")]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, u"Alarm", u"Rauchmelder")

        AlexaHelper.sendTTS(u"Es brennt", priority = NotificationHelper.PRIORITY_ALERT)
