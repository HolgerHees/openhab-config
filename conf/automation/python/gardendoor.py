from openhab import rule, Registry, logger
from openhab.triggers import ItemStateChangeTrigger

from shared.notification import NotificationHelper

from custom.frigate import FrigateHelper

from datetime import datetime, timedelta
import threading

import scope

@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_Streedside_Gardendoor_Bell_State", state=scope.OPEN)
    ]
)
class BellNotification:
    def execute(self, module, input):
        if Registry.getItemState("pOutdoor_Streedside_Gardendoor_Bell_Last_Change").getZonedDateTime() < ( datetime.now().astimezone() - timedelta(seconds=30) ):
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "Klingel", "Es klingelt", FrigateHelper.getLatestSnapshotUrl("streedside") )

        Registry.getItem("pOutdoor_Streedside_Gardendoor_Bell_Last_Change").postUpdate(datetime.now().astimezone())

        FrigateHelper.createEvent("streedside", "bell")

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
        Registry.getItem("pOutdoor_Streedside_Gardendoor_Opener_Timer").postUpdate(scope.OFF)
        Registry.getItem("pOutdoor_Streedside_Gardendoor_Opener_Powered").sendCommandIfDifferent(scope.OFF)

    def execute(self, module, input):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

        if input["newState"] == scope.ON:
            Registry.getItem("pOutdoor_Streedside_Gardendoor_Opener_Powered").sendCommand(scope.ON)
            self.timer = threading.Timer(3.0, self.callback)
            self.timer.start()
        else:
            Registry.getItem("pOutdoor_Streedside_Gardendoor_Opener_Powered").sendCommandIfDifferent(scope.OFF)
