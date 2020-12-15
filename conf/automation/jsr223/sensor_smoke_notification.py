from shared.helper import rule, ItemStateChangeTrigger, sendNotification


@rule("scene_contact_notifications.py")
class SmokeDetectorNotificationsRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Smoke_Detector_State",state="OPEN")]

    def execute(self, module, input):
        sendNotification("Alarm", u"Rauchmelder") 
