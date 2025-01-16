from java.time import ZonedDateTime

from shared.helper import rule, getItemState, postUpdateIfChanged, NotificationHelper
from shared.triggers import ItemStateChangeTrigger, CronTrigger


@rule()
class SensorNukiBatteryDetail:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("pGF_Corridor_Lock_Battery_Critical"),
            ItemStateChangeTrigger("pGF_Corridor_Lock_Timestamp")
        ]

    def execute(self, module, input):
        now = ZonedDateTime.now()

        msg = []
        if getItemState("pGF_Corridor_Lock_Battery_Critical") == ON:
            msg.append("Batterie")

        if getItemState("pGF_Corridor_Lock_Timestamp").getZonedDateTime().plusMinutes(120).isBefore(now) == OFF:
            msg.append("Verbindung")

        if len(msg) == 0:
            msg.append("Alles ok")

        postUpdateIfChanged("pGF_Corridor_Lock_State_Device_Info", ",".join(msg))


@rule()
class SensorNukiLockDetail:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Corridor_Lock_State")
        ]

    def execute(self, module, input):
        state = input["event"].getItemState().intValue()
        if state in [1,4]: # abgeschlossen
            postUpdateIfChanged("pGF_Corridor_Lock_Action", 2)
        elif state in [2,3]: # aufgeschlossen
            postUpdateIfChanged("pGF_Corridor_Lock_Action", 1)
        else:
            postUpdateIfChanged("pGF_Corridor_Lock_Action", 0)
        #if state in [1,4]: # abgeschlossen
        #    postUpdateIfChanged("pGF_Corridor_Lock_Action", 2)
        #elif state in [0,2,3,5,6,7]: # aufgeschlossen
        #    postUpdateIfChanged("pGF_Corridor_Lock_Action", 1)
