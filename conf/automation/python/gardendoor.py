from openhab import rule, Registry, Timer, logger
from openhab.triggers import ItemStateChangeTrigger

from shared.notification import NotificationHelper

from datetime import datetime, timedelta


@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_Streedside_Gardendoor_Bell_State", state="OPEN")
    ]
)
class BellNotification:
    def execute(self, module, input):
        if Registry.getItemState("pOutdoor_Streedside_Gardendoor_Bell_Last_Change") > ( datetime.now().astimezone() - timedelta(seconds=30) ):
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "Klingel", "Es klingelt", "https://smartmarvin.de/cameraStreedsideImage" )

        Registry.getItem("pOutdoor_Streedside_Gardendoor_Bell_Last_Change").postUpdate(datetime.now().astimezone())

@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_Streedside_Gardendoor_Opener_Timer")
    ]
)
class OpenerControl:
    def __init__(self):
        self.timer = None

    def callback(self):
        self.timer = None
        Registry.getItem("pOutdoor_Streedside_Gardendoor_Opener_Timer").postUpdate(OFF)
        Registry.getItem("pOutdoor_Streedside_Gardendoor_Opener_Powered").sendCommandIfDifferent(OFF)

    def execute(self, module, input):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

        if input["newState"] == ON:
            Registry.getItem("pOutdoor_Streedside_Gardendoor_Opener_Powered").sendCommand(ON)
            self.timer = Timer.createTimeout(3.0, self.callback)
        else:
            Registry.getItem("pOutdoor_Streedside_Gardendoor_Opener_Powered").sendCommandIfDifferent(OFF)
