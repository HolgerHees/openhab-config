from openhab import rule
from openhab.triggers import ItemStateChangeTrigger

from shared.notification import NotificationHelper

from custom.voice import VoiceAssistentHelper

import scope


@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Smoke_Detector_State",state=scope.OPEN)
    ]
)
class Main:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, "Alarm", "Rauchmelder")

        VoiceAssistentHelper.sendTTS("Es brennt", priority = NotificationHelper.PRIORITY_ALERT)
