from shared.helper import rule, postUpdateIfChanged, getItemState, getThing, startTimer
from shared.triggers import CronTrigger, ThingStatusChangeTrigger

@rule()
class AlexaState:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ThingStatusChangeTrigger("amazonechocontrol:account:account1")
        ]

        startTimer(self.log, 5, self.check)

    def check(self):
        thing = getThing("amazonechocontrol:account:account1")
        status = thing.getStatus()

        if status.toString() != "ONLINE":
            info = thing.getStatusInfo()
            postUpdateIfChanged("eOther_Error_Alexa_Message", "Thing: {}".format(info.toString()))
        else:
            postUpdateIfChanged("eOther_Error_Alexa_Message","")

    def execute(self, module, input):
        self.check()
