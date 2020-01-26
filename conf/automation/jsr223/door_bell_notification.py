from custom.helper import rule, getNow, itemStateOlderThen, sendNotification, postUpdate
from core.triggers import ItemStateChangeTrigger


@rule("door_bell_notification.py")
class DoorBellNotificationRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Bell_State", state="OPEN")]

    def execute(self, module, input):
        if itemStateOlderThen("Bell_Last_Change", getNow().minusSeconds(30)):
            sendNotification("Klingel", "Es klingelt", "https://smartmarvin.de/cameraStrasseImage")

        postUpdate("Bell_Last_Change", DateTimeType())
