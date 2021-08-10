from shared.helper import rule, getItemState, sendCommand
from shared.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime


@rule("lights_indoor_auto_attic.py")
class LightsIndoorAutoAtticRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 1 5,8,20,23 * * ?"),
            ItemStateChangeTrigger("Attic_Light_Mode")
        ]

    def execute(self, module, input):
        hour = ZonedDateTime.now().getHour()

        state = getItemState("pOther_Manual_State_Auto_Attic_Light").intValue();
        
        if state == 2:
            if hour == 5:
                sendCommand("pFF_Attic_Socket_Powered", ON)
            elif hour == 23:
                sendCommand("pFF_Attic_Socket_Powered", OFF)
        elif state == 3:
            if hour == 8:
                sendCommand("pFF_Attic_Socket_Powered", ON)
            elif hour == 20:
                sendCommand("pFF_Attic_Socket_Powered", OFF)
