from java.time import ZonedDateTime

from shared.helper import rule, itemStateOlderThen, postUpdate, NotificationHelper
from shared.triggers import ItemStateChangeTrigger


@rule()
class DoorBellNotification:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOutdoor_Streedside_Gardendoor_Bell_State", state="OPEN")]

    def execute(self, module, input):
        if itemStateOlderThen("pOutdoor_Streedside_Gardendoor_Bell_Last_Change", ZonedDateTime.now().minusSeconds(30)):
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "Klingel", "Es klingelt", "https://smartmarvin.de/cameraStreedsideImage" )

        postUpdate("pOutdoor_Streedside_Gardendoor_Bell_Last_Change", DateTimeType())



