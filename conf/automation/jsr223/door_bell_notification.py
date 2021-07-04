from shared.helper import rule, itemStateOlderThen, sendNotification, postUpdate
from core.triggers import ItemStateChangeTrigger
from java.time import ZonedDateTime

@rule("door_bell_notification.py")
class DoorBellNotificationRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOutdoor_Streedside_Gardendoor_Bell_State", state="OPEN")]

    def execute(self, module, input):
        if itemStateOlderThen("pOutdoor_Streedside_Gardendoor_Bell_Last_Change", ZonedDateTime.now().minusSeconds(30)):
            sendNotification("Klingel", "Es klingelt", "https://smartmarvin.de/cameraStrasseImage" )

        postUpdate("pOutdoor_Streedside_Gardendoor_Bell_Last_Change", DateTimeType())
 
