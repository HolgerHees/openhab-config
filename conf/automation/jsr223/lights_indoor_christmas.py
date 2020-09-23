from custom.helper import rule, getNow, getItemState, sendCommand, createTimer
from core.triggers import CronTrigger, ItemStateChangeTrigger


@rule("lights_indoor_auto_christmas.py")
class LightsOnRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("State_Presence")
        ]
        
    def callback(self,state):
        sendCommand("Socket_Mobile_2", state)

    def execute(self, module, input):
        if getItemState("Auto_Christmas") == ON:
            if input["event"].getItemState().intValue() == 1:
                sendCommand("Socket_Floor", ON)
                sendCommand("Socket_Livingroom_Couch", ON)
                sendCommand("Socket_Livingroom_Fireplace", ON)
                sendCommand("Socket_Mobile_1", ON)

                # must be a timer, otherwise sometimes it does not work. Maybe a conflict with Socket_Mobile_1 action
                timer = createTimer(self.log, 1.0,self.callback,[ON])
                timer.start()
                
            else:
                sendCommand("Socket_Floor", OFF)
                sendCommand("Socket_Livingroom_Couch", OFF)
                sendCommand("Socket_Livingroom_Fireplace", OFF)
                sendCommand("Socket_Mobile_1", OFF)

                # must be a timer, otherwise sometimes it does not work. Maybe a conflict with Socket_Mobile_1 action
                timer = createTimer(self.log, 1.0,self.callback,[OFF])
                timer.start()
