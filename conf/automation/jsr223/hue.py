from shared.helper import rule, postUpdateIfChanged, getThing, startTimer
from shared.triggers import ThingStatusChangeTrigger


@rule()
class HueState:
    def __init__(self):
        self.triggers = [
            ThingStatusChangeTrigger("hue:bridge-api2:default")
        ]

        startTimer(self.log, 5, self.check)

    def check(self):
        thing = getThing("hue:bridge-api2:default")
        status = thing.getStatus()

        if status.toString() != "ONLINE":
            info = thing.getStatusInfo()
            postUpdateIfChanged("eOther_Error_Hue_Message", "Thing: {}".format(info.toString()))
        else:
            postUpdateIfChanged("eOther_Error_Hue_Message","")

    def execute(self, module, input):
        self.check()
