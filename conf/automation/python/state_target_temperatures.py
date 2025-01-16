from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper


@rule()
class Main:
    def buildTriggers(self):
        return ToolboxHelper.getGroupMemberTrigger(ItemStateChangeTrigger, "eOther_Target_Temperatures")

    def execute(self, module, input):
        max_temperature = 0.0
        for item in Registry.getItem("eOther_Target_Temperatures").getAllGroupMembers():
            temperature = item.getState().floatValue()
            if temperature > max_temperature:
                max_temperature = temperature

        Registry.getItem("pGF_Utilityroom_Ventilation_Comfort_Temperature").sendCommandIfDifferent(max_temperature)

