from custom.helper import rule, getItemState, postUpdate, postUpdateIfChanged, itemLastUpdateOlderThen, itemStateNewerThen, getNow
from core.actions import Transformation
from core.triggers import CronTrigger, ItemStateChangeTrigger


@rule("roboter_robonect.py")
class MoverStatusRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 2,17,32,47 * * * ?"),
            ItemStateChangeTrigger("MowerDuration"),
            ItemStateChangeTrigger("MowerStatus")
        ]

    def execute(self, module, input):
        moverStatus = getItemState("MowerStatus").toString()

        if itemLastUpdateOlderThen("MowerWlanSignal", getNow().minusMinutes(60)):
            if moverStatus != "98":
                postUpdate("MowerStatus", 98)
                postUpdate("MowerStatusFormatted", Transformation.transform("MAP", "robonect_status.map", "98"))
        else:
            seconds = getItemState("MowerDuration").intValue()
            hours = seconds / (60 * 60)
            seconds = seconds % (60 * 60)
            minutes = seconds / 60
            #seconds = seconds % 60

            msg = u"{} seit ".format(Transformation.transform("MAP", "robonect_status.map", moverStatus))
            if hours < 10: msg = u"{}0".format(msg)
            msg = u"{}{}:".format(msg,hours)
            if minutes < 10: msg = u"{}0".format(msg)
            msg = u"{}{}:".format(msg,minutes)

            postUpdateIfChanged("MowerStatusFormatted", msg)


@rule("roboter_robonect.py")
class MoverTimerRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("MowerTimerStatus"),
            ItemStateChangeTrigger("MowerNextTimer")
        ]

    def execute(self, module, input):
        timerStatus = getItemState("MowerTimerStatus").toString()
        msg = u""

        if timerStatus != "STANDBY":
            msg = u"{}{}".format( msg, Transformation.transform("MAP", "robonect_timer_status.map", timerStatus) )
        else:
            if itemStateNewerThen("MowerNextTimer", getNow().plusHours(24 * 4)):
                msg = u"{}Starte am {}".format(msg,getItemState("MowerNextTimer").format("%1$td.%1$tm %1$tH:%1$tM"))
            else:
                msg = u"{}Starte {}".format(msg,getItemState("MowerNextTimer").format("%1$tA %1$tH:%1$tM"))

        postUpdateIfChanged("MowerTimerStatusFormatted", msg)
