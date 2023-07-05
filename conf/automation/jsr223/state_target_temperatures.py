from shared.helper import rule, getItemState, sendCommandIfChanged, getGroupMemberChangeTrigger, getGroupMember
from shared.triggers import ItemStateChangeTrigger

@rule()
class StateTargetTemperatures:
    def __init__(self):
        self.triggers = getGroupMemberChangeTrigger("eOther_Target_Temperatures")

    def execute(self, module, input):

        max_temperature = 0.0
        for item in getGroupMember("eOther_Target_Temperatures"):
            temperature = item.getState().floatValue()
            if temperature > max_temperature:
                max_temperature = temperature

        sendCommandIfChanged("pGF_Utilityroom_Ventilation_Comfort_Temperature", max_temperature)

