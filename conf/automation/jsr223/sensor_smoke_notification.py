from shared.helper import rule, ItemStateChangeTrigger, NotificationHelper


@rule("scene_contact_notifications.py")
class SmokeDetectorNotificationsRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Smoke_Detector_State",state="OPEN")]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, "Alarm", u"Rauchmelder")
