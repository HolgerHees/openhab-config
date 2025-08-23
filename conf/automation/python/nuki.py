from openhab import rule, logger, Registry
from openhab.triggers import SystemStartlevelTrigger, GenericCronTrigger, ItemStateChangeTrigger

from datetime import datetime, timedelta

import scope


@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        GenericCronTrigger("0 */5 * * * ?"),
        ItemStateChangeTrigger("pGF_Corridor_Lock_Battery_Critical")
#        ItemStateChangeTrigger("pGF_Corridor_Lock_Timestamp")
    ]
)
class BatteryDetail:
    def execute(self, module, input):
        msg = []
        if Registry.getItemState("pGF_Corridor_Lock_Battery_Critical") == scope.ON:
            msg.append("Batterie")

        if ( Registry.getItemState("pGF_Corridor_Lock_Timestamp").getZonedDateTime() + timedelta(minutes=120) ) < datetime.now().astimezone():
            msg.append("Verbindung")

        if len(msg) == 0:
            msg.append("Alles ok")

        Registry.getItem("pGF_Corridor_Lock_State_Device_Info").postUpdateIfDifferent(",".join(msg))


@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Corridor_Lock_State")
    ]
)
class LockDetail:
    def execute(self, module, input):
        state = input["event"].getItemState().intValue()
        if state in [1,4]: # abgeschlossen
            Registry.getItem("pGF_Corridor_Lock_Action").postUpdateIfDifferent(2)
        elif state in [2,3]: # aufgeschlossen
            Registry.getItem("pGF_Corridor_Lock_Action").postUpdateIfDifferent(1)
        else:
            Registry.getItem("pGF_Corridor_Lock_Action").postUpdateIfDifferent(0)
        #if state in [1,4]: # abgeschlossen
        #    Registry.getItem("pGF_Corridor_Lock_Action").postUpdateIfDifferent(2)
        #elif state in [0,2,3,5,6,7]: # aufgeschlossen
        #    Registry.getItem("pGF_Corridor_Lock_Action").postUpdateIfDifferent(1)
