from java.time import ZonedDateTime

from shared.helper import rule, getItemState, sendCommand
from shared.triggers import CronTrigger, ItemStateChangeTrigger


@rule()
class LightsIndoorAttic:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 1 5,8,20,23 * * ?"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light")
        ]

    def execute(self, module, input):
        hour = ZonedDateTime.now().getHour()

        state = getItemState("pOther_Manual_State_Auto_Attic_Light").intValue();
        
        if state == 2:
            if hour == 5:
                sendCommand("pMobile_Socket_7_Powered", ON)
            elif hour == 23:
                sendCommand("pMobile_Socket_7_Powered", OFF)
        elif state == 3:
            if hour == 8:
                sendCommand("pMobile_Socket_7_Powered", ON)
            elif hour == 20:
                sendCommand("pMobile_Socket_7_Powered", OFF)
