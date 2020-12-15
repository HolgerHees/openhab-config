from shared.helper import rule, getNow, getItemState, sendCommand, createTimer
from core.triggers import CronTrigger, ItemStateChangeTrigger


@rule("lights_indoor_auto_christmas.py")
class LightsOnRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State")
        ]
        
    def callback(self,state):
        sendCommand("eMobile_Socket_2_Powered", state)

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Christmas") == ON:
            if input["event"].getItemState().intValue() == 1:
                sendCommand("pGF_Corridor_Socket_Powered", ON)
                sendCommand("pGF_Livingroom_Socket_Couch_Powered", ON)
                sendCommand("pGF_Livingroom_Socket_Fireplace_Powered", ON)
                sendCommand("eMobile_Socket_1_Powered", ON)

                # must be a timer, otherwise sometimes it does not work. Maybe a conflict with eMobile_Socket_1_Powered action
                timer = createTimer(self.log, 1.0,self.callback,[ON])
                timer.start()
                
            else:
                sendCommand("pGF_Corridor_Socket_Powered", OFF)
                sendCommand("pGF_Livingroom_Socket_Couch_Powered", OFF)
                sendCommand("pGF_Livingroom_Socket_Fireplace_Powered", OFF)
                sendCommand("eMobile_Socket_1_Powered", OFF)

                # must be a timer, otherwise sometimes it does not work. Maybe a conflict with eMobile_Socket_1_Powered action
                timer = createTimer(self.log, 1.0,self.callback,[OFF])
                timer.start()

@rule("lights_indoor_auto_christmas.py")                
class OutdoorLightsOnRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Automatic_State_Outdoorlights"),
            ItemStateChangeTrigger("pOther_Presence_State")
        ]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Christmas") == ON:
            if input['event'].getItemName() == "pOther_Automatic_State_Outdoorlights":
                if input["event"].getItemState() == ON:
                    sendCommand("pOutdoor_Streeside_Socket_Powered", ON)
                else:
                    sendCommand("pOutdoor_Streeside_Socket_Powered", OFF)
            else:
                if input["event"].getItemState().intValue() == 1 and getItemState("pOther_Automatic_State_Outdoorlights") == ON:
                    sendCommand("pOutdoor_Streeside_Socket_Powered", ON)
                elif input["event"].getItemState().intValue() == 2:
                    sendCommand("pOutdoor_Streeside_Socket_Powered", OFF)
