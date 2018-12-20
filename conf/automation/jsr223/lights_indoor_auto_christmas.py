from marvin.helper import rule, getNow, getItemState, sendCommand
from core.triggers import CronTrigger, ItemStateChangeTrigger


@rule("lights_indoor_auto_christmas.py")
class LightsOnRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 0 16 * * ?"),
            ItemStateChangeTrigger("State_Sleeping", "OFF")
        ]

    def execute(self, module, input):
        if getItemState("Auto_Christmas") == ON:
            now = getNow()
            hour = now.getHourOfDay()
            minute = now.getMinuteOfHour()

            if (hour == 16 and minute == 0) or (hour < 10 and getItemState("State_Sleeping") == OFF and getItemState("State_Present") == ON):
                sendCommand("Socket_Floor", ON)
                sendCommand("Socket_Livingroom_Couch", ON)
                sendCommand("Socket_Livingroom_Fireplace", ON)
                sendCommand("Socket_Mobile_1", ON)
                sendCommand("Socket_Mobile_2", ON)


@rule("lights_indoor_auto_christmas.py")
class LightsOffRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 0 22 * * ?"),
            ItemStateChangeTrigger("State_Present", "OFF"),
            ItemStateChangeTrigger("State_Sleeping", "ON")
        ]

    def execute(self, module, input):
        if getItemState("Auto_Christmas") == ON:
            now = getNow()
            hour = now.getHourOfDay()
            minute = now.getMinuteOfHour()

            if (getItemState("State_Present") == OFF and ((hour > 3 and hour < 10) or (hour == 22 and minute == 0))) or getItemState("State_Sleeping") == ON:
                sendCommand("Socket_Floor", OFF)
                sendCommand("Socket_Livingroom_Couch", OFF)
                sendCommand("Socket_Livingroom_Fireplace", OFF)
                sendCommand("Socket_Mobile_1", OFF)
                sendCommand("Socket_Mobile_2", OFF)
