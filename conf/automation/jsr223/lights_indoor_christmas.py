from shared.helper import rule, getItemState, sendCommand
from shared.triggers import CronTrigger, ItemStateChangeTrigger

from custom.presence import PresenceHelper


@rule()
class LightsIndoorChristmans:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State")
        ]
        
    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Christmas") != ON:
            return
          
        if input["event"].getItemState().intValue() == PresenceHelper.STATE_PRESENT:
            sendCommand("pGF_Corridor_Socket_Powered", ON)
            sendCommand("pGF_Livingroom_Socket_Couch_Powered", ON)
            sendCommand("pGF_Livingroom_Socket_Fireplace_Powered", ON)
            sendCommand("pMobile_Socket_1_Powered", ON)
            sendCommand("pMobile_Socket_2_Powered", ON)
            sendCommand("pMobile_Socket_3_Powered", ON)
            sendCommand("pMobile_Socket_4_Powered", ON)
            
        elif input["event"].getItemState().intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING]:
            sendCommand("pGF_Corridor_Socket_Powered", OFF)
            sendCommand("pGF_Livingroom_Socket_Couch_Powered", OFF)
            sendCommand("pGF_Livingroom_Socket_Fireplace_Powered", OFF)
            sendCommand("pMobile_Socket_1_Powered", OFF)
            sendCommand("pMobile_Socket_2_Powered", OFF)
            sendCommand("pMobile_Socket_3_Powered", OFF)
            sendCommand("pMobile_Socket_4_Powered", OFF)

@rule()
class LightsOutdoorChristmans:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Automatic_State_Outdoorlights"),
            ItemStateChangeTrigger("pOther_Presence_State")
        ]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Christmas") != ON:
            return
          
        if input['event'].getItemName() == "pOther_Automatic_State_Outdoorlights":
            if input["event"].getItemState() == ON:
                sendCommand("pOutdoor_Streeside_Socket_Powered", ON)
            else:
                sendCommand("pOutdoor_Streeside_Socket_Powered", OFF)
        else:
            if input["event"].getItemState().intValue() == PresenceHelper.STATE_PRESENT:
                if getItemState("pOther_Automatic_State_Outdoorlights") == ON:
                    sendCommand("pOutdoor_Streeside_Socket_Powered", ON)
            elif input["event"].getItemState().intValue() == PresenceHelper.STATE_SLEEPING:
                sendCommand("pOutdoor_Streeside_Socket_Powered", OFF)
