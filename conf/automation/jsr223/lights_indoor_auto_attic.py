from marvin.helper import rule, getNow, getItemState, sendCommand
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

        if getItemState("Auto_Attic_Light").intValue() == 2:
            if 5 <= hour < 23:
                sendCommand("Socket_Attic", ON)
            else:
                sendCommand("Socket_Attic", OFF)
        elif getItemState("Auto_Attic_Light").intValue() == 3:
            if 8 <= hour < 20:
                sendCommand("Socket_Attic", ON)
            else:
                sendCommand("Socket_Attic", OFF)
