from custom.helper import rule, ItemStateChangeTrigger, sendNotification


@rule("scene_contact_notifications.py")
class SmokeDetectorNotificationsRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Smoke_Detector",state="OPEN")]

    def execute(self, module, input):
        sendNotification("Alarm", u"Rauchmelder") 
