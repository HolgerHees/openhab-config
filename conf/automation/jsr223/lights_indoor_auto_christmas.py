from marvin.helper import rule, getNow, getItemState, sendCommand
from openhab.triggers import CronTrigger, ItemStateChangeTrigger


@rule("lights_indoor_auto_christmas.py")
class LightsOnRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 0 16 * * ?"),
            ItemStateChangeTrigger("State_Sleeping", "OFF")
        ]

    def execute(self, module, input):
        if getItemState("Auto_Christmas") == ON and (getItemState("Socket_Livingroom") == OFF or getItemState("Socket_Floor") == OFF):
            now = getNow()
            hour = now.getHourOfDay()
            minute = now.getMinuteOfHour()

            if (hour == 16 and minute == 0) or (hour < 10 and getItemState("State_Sleeping") == OFF or getItemState("State_Present") == ON):
                sendCommand("Socket_Livingroom", ON)


@rule("lights_indoor_auto_christmas.py")
class LightsOffRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 0 22 * * ?"),
            ItemStateChangeTrigger("State_Present", "OFF"),
            ItemStateChangeTrigger("State_Sleeping", "ON")
        ]

    def execute(self, module, input):
        if getItemState("Auto_Christmas") == ON and (getItemState("Socket_Livingroom") == ON or getItemState("Socket_Floor") == ON):
            now = getNow()
            hour = now.getHourOfDay()
            minute = now.getMinuteOfHour()

            if (getItemState("State_Present") == OFF and ((hour > 3 and hour < 10) or (hour == 22 and minute == 0))) or getItemState(
                    "State_Sleeping") == ON:
                sendCommand("Socket_Livingroom", OFF)
