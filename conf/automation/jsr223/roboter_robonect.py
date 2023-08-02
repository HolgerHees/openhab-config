from java.time import ZonedDateTime

from shared.helper import rule, getItemState, postUpdate, postUpdateIfChanged, itemLastUpdateOlderThen, itemStateNewerThen, getThing, startTimer
from shared.actions import Transformation
from shared.triggers import CronTrigger, ItemStateChangeTrigger, ThingStatusChangeTrigger
 

#postUpdate("pOutdoor_Mower_WlanSignal",0)
#postUpdate("pOutdoor_Mower_Duration",0)

@rule()
class RoboterRobonectState:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ThingStatusChangeTrigger("robonect:mower:automower")
        ]

        startTimer(self.log, 5, self.check)

    def check(self):
        thing = getThing("robonect:mower:automower")
        status = thing.getStatus()
        info = thing.getStatusInfo()

        if status is not None and info is not None:
            #self.log.info(u"Home Connect bridge status: '{}',  detail: '{}'".format(status.toString(),info.toString()))
            if status.toString() == "ONLINE":
                postUpdateIfChanged("pOutdoor_Mower_Winter_Mode", OFF)

    def execute(self, module, input):
        self.check()

@rule()
class RoboterRobonectAction:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 2,17,32,47 * * * ?"),
            ItemStateChangeTrigger("pOutdoor_Mower_Duration"),
            ItemStateChangeTrigger("pOutdoor_Mower_Status")
        ]

    def execute(self, module, input):
        moverStatus = getItemState("pOutdoor_Mower_Status").toString()

        if itemLastUpdateOlderThen("pOutdoor_Mower_WlanSignal", ZonedDateTime.now().minusMinutes(60)):
            if moverStatus != "98":
                postUpdate("pOutdoor_Mower_Status", 98)
                postUpdate("pOutdoor_Mower_StatusFormatted", Transformation.transform("MAP", "robonect_status.map", "98"))
        else:
            seconds = getItemState("pOutdoor_Mower_Duration").intValue()
            hours = seconds / (60 * 60)
            seconds = seconds % (60 * 60)
            minutes = seconds / 60
            #seconds = seconds % 60

            msg = u"{} seit ".format(Transformation.transform("MAP", "robonect_status.map", moverStatus))
            if hours < 10: msg = u"{}0".format(msg)
            msg = u"{}{}:".format(msg,hours)
            if minutes < 10: msg = u"{}0".format(msg)
            msg = u"{}{}:".format(msg,minutes)

            postUpdateIfChanged("pOutdoor_Mower_StatusFormatted", msg)


@rule()
class RoboterRobonectTimer:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_Mower_TimerStatus"),
            ItemStateChangeTrigger("pOutdoor_Mower_NextTimer")
        ]

    def execute(self, module, input):
        timerStatus = getItemState("pOutdoor_Mower_TimerStatus").toString()
        msg = u""

        if timerStatus != "STANDBY":
            msg = u"{}{}".format( msg, Transformation.transform("MAP", "robonect_timer_status.map", timerStatus) )
        else:
            if itemStateNewerThen("pOutdoor_Mower_NextTimer", ZonedDateTime.now().plusHours(24 * 4)):
                msg = u"{}Starte am {}".format(msg,getItemState("pOutdoor_Mower_NextTimer").format("%1$td.%1$tm %1$tH:%1$tM"))
            else:
                msg = u"{}Starte {}".format(msg,getItemState("pOutdoor_Mower_NextTimer").format("%1$tA %1$tH:%1$tM"))

        postUpdateIfChanged("pOutdoor_Mower_TimerStatusFormatted", msg)
