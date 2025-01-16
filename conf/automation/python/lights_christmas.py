from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from custom.presence import PresenceHelper


@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Presence_State")
    ]
)
class Indoor:
    def execute(self, module, input):
        if Registry.getItemState("pOther_Manual_State_Auto_Christmas") != ON:
            return
          
        if input["event"].getItemState().intValue() == PresenceHelper.STATE_PRESENT:
            Registry.getItem("pGF_Corridor_Socket_Powered").sendCommand(ON)
            Registry.getItem("pGF_Livingroom_Socket_Couch_Powered").sendCommand(ON)
            Registry.getItem("pGF_Livingroom_Socket_Fireplace_Powered").sendCommand(ON)
            Registry.getItem("pMobile_Socket_1_Powered").sendCommand(ON)
            Registry.getItem("pMobile_Socket_2_Powered").sendCommand(ON)
            Registry.getItem("pMobile_Socket_3_Powered").sendCommand(ON)
            Registry.getItem("pMobile_Socket_4_Powered").sendCommand(ON)
            
        elif input["event"].getItemState().intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING]:
            Registry.getItem("pGF_Corridor_Socket_Powered").sendCommand(OFF)
            Registry.getItem("pGF_Livingroom_Socket_Couch_Powered").sendCommand(OFF)
            Registry.getItem("pGF_Livingroom_Socket_Fireplace_Powered").sendCommand(OFF)
            Registry.getItem("pMobile_Socket_1_Powered").sendCommand(OFF)
            Registry.getItem("pMobile_Socket_2_Powered").sendCommand(OFF)
            Registry.getItem("pMobile_Socket_3_Powered").sendCommand(OFF)
            Registry.getItem("pMobile_Socket_4_Powered").sendCommand(OFF)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Automatic_State_Outdoorlights"),
        ItemStateChangeTrigger("pOther_Presence_State")
    ]
)
class Outdoor:
    def execute(self, module, input):
        if Registry.getItemState("pOther_Manual_State_Auto_Christmas") != ON:
            return
          
        if input['event'].getItemName() == "pOther_Automatic_State_Outdoorlights":
            if input["event"].getItemState() == ON:
                Registry.getItem("pOutdoor_Streeside_Socket_Powered").sendCommand(ON)
            else:
                Registry.getItem("pOutdoor_Streeside_Socket_Powered").sendCommand(OFF)
        else:
            if input["event"].getItemState().intValue() == PresenceHelper.STATE_PRESENT:
                if Registry.getItemState("pOther_Automatic_State_Outdoorlights") == ON:
                    Registry.getItem("pOutdoor_Streeside_Socket_Powered").sendCommand(ON)
            elif input["event"].getItemState().intValue() == PresenceHelper.STATE_SLEEPING:
                Registry.getItem("pOutdoor_Streeside_Socket_Powered").sendCommand(OFF)
