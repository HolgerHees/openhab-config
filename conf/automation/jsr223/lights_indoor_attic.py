from shared.helper import rule, getNow, getItemState, sendCommand
from core.triggers import CronTrigger, ItemStateChangeTrigger


@rule("lights_indoor_auto_attic.py")
class LightsIndoorAutoAtticRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 1 5,8,20,23 * * ?"),
            ItemStateChangeTrigger("Attic_Light_Mode")
        ]

    def execute(self, module, input):
        hour = getNow().getHourOfDay()

        state = getItemState("Auto_Attic_Light").intValue();
        
        if state == 2:
            if hour == 5:
                sendCommand("pAttic_Socket_Powered", ON)
            elif hour == 23:
                sendCommand("pAttic_Socket_Powered", OFF)
        elif state == 3:
            if hour == 8:
                sendCommand("pAttic_Socket_Powered", ON)
            elif hour == 20:
                sendCommand("pAttic_Socket_Powered", OFF)
