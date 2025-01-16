from openhab import rule
from openhab.triggers import ItemStateChangeTrigger

from shared.notification import NotificationHelper

from custom.alexa import AlexaHelper


@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Smoke_Detector_State",state="OPEN")
    ]
)
class Main:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, "Alarm", "Rauchmelder")

        AlexaHelper.sendTTS("Es brennt", priority = NotificationHelper.PRIORITY_ALERT)
