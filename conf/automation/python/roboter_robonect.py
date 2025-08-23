from openhab import rule, Registry
from openhab.actions import Transformation
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, ThingStatusChangeTrigger, SystemStartlevelTrigger

from shared.toolbox import ToolboxHelper
 
from datetime import datetime, timedelta
import math

import scope


@rule(
    triggers = [
        #GenericCronTrigger("*/15 * * * * ?"),
        SystemStartlevelTrigger(80),
        ThingStatusChangeTrigger("robonect:mower:automower")
    ]
)
class State:
    def execute(self, module, input):
        thing = Registry.getThing("robonect:mower:automower")
        status = thing.getStatus()
        info = thing.getStatusInfo()

        if status is not None and info is not None:
            #self.logger.info("Home Connect bridge status: '{}',  detail: '{}'".format(status.toString(),info.toString()))
            if status.toString() == "ONLINE":
                Registry.getItem("pOutdoor_Mower_Winter_Mode").postUpdateIfDifferent(scope.OFF)

@rule(
    triggers = [
        GenericCronTrigger("0 2,17,32,47 * * * ?"),
        ItemStateChangeTrigger("pOutdoor_Mower_Duration"),
        ItemStateChangeTrigger("pOutdoor_Mower_Status")
    ]
)
class Action:
    def execute(self, module, input):
        moverStatus = Registry.getItemState("pOutdoor_Mower_Status").toString()

        if Registry.getItem("pOutdoor_Mower_WlanSignal").getLastStateUpdate() < datetime.now().astimezone() - timedelta(minutes=60):
            if moverStatus != "98":
                #postUpdate("pOutdoor_Mower_Status", 98)
                Registry.getItem("pOutdoor_Mower_StatusFormatted").postUpdate(Transformation.transform("MAP", "robonect_status.map", "98"))
        else:
            seconds =  Registry.getItemState("pOutdoor_Mower_Duration").intValue()
            hours = math.floor(seconds / (60 * 60))
            seconds = math.floor(seconds % (60 * 60))
            minutes = math.floor(seconds / 60)
            #seconds = seconds % 60

            msg = "{} seit ".format(Transformation.transform("MAP", "robonect_status.map", moverStatus))
            if hours < 10: msg = "{}0".format(msg)
            msg = "{}{}:".format(msg,hours)
            if minutes < 10: msg = "{}0".format(msg)
            msg = "{}{}".format(msg,minutes)

            Registry.getItem("pOutdoor_Mower_StatusFormatted").postUpdateIfDifferent(msg)


@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_Mower_TimerStatus"),
        ItemStateChangeTrigger("pOutdoor_Mower_NextTimer")
    ]
)
class Timer:
    def execute(self, module, input):
        timerStatus = Registry.getItemState("pOutdoor_Mower_TimerStatus").toString()
        msg = ""

        if timerStatus != "STANDBY":
            msg = "{}{}".format( msg, Transformation.transform("MAP", "robonect_timer_status.map", timerStatus) )
        else:
            if Registry.getItem("pOutdoor_Mower_NextTimer").getLastStateUpdate() > datetime.now().astimezone() + timedelta(hours=24 * 4):
                msg = "{}Starte am {}".format(msg, Registry.getItemState("pOutdoor_Mower_NextTimer").getZonedDateTime().strftime("%d.%m %H:%M"))
            else:
                msg = "{}Starte {}".format(msg, Registry.getItemState("pOutdoor_Mower_NextTimer").getZonedDateTime().strftime("%A %H:%M"))

        Registry.getItem("pOutdoor_Mower_TimerStatusFormatted").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        GenericCronTrigger("0 * * * * ?"),
        #GenericCronTrigger("0 0 * * * ?"),
        ItemStateChangeTrigger("pOutdoor_Mower_Status"),
        ItemStateChangeTrigger("pOutdoor_Mower_Winter_Mode")
    ]
)
class StateMessages:
    def execute(self, module, input):
        active = []

        if Registry.getItemState("pOutdoor_Mower_Winter_Mode") == scope.OFF:
            mower_state = Registry.getItemState("pOutdoor_Mower_Status")
            if mower_state != scope.NULL and ( mower_state.intValue() == 7 or mower_state.intValue() == 8 or mower_state.intValue() == 98 ):
                is_deep_sleep = False
                if mower_state.intValue() == 98:
                    previous_state = ToolboxHelper.getPreviousPersistedState("pOutdoor_Mower_Status")
                    if previous_state != scope.NULL and previous_state.intValue() == 17:
                        is_deep_sleep = True
                if not is_deep_sleep:
                    active.append("Fehler")

        if len(active) == 0:
            active.append("Alles ok")

        Registry.getItem("pOutdoor_Mower_State_Message").postUpdateIfDifferent(", ".join(active))

