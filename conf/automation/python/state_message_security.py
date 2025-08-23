from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper

import scope


@rule
class Main:
    def buildTriggers(self):
        triggers = []
        for item in Registry.getItem("gGF_Sensor_Doors").getAllMembers():
            triggers.append(ItemStateChangeTrigger(item.getName()))
        for item in Registry.getItem("gGF_Sensor_Window").getAllMembers():
            triggers.append(ItemStateChangeTrigger(item.getName()))
        for item in Registry.getItem("gFF_Sensor_Window").getAllMembers():
            triggers.append(ItemStateChangeTrigger(item.getName()))
        triggers.append(ItemStateChangeTrigger("pToolshed_Openingcontact_Door_State"))
        return triggers

    def execute(self, module, input):
        active = []

        count = len(ToolboxHelper.getFilteredGroupMember("gGF_Sensor_Doors", scope.OPEN))
        count += 1 if Registry.getItemState("pToolshed_Openingcontact_Door_State") == scope.OPEN else 0
        if count > 0:
            if count == 1:
                active.append("1 Tür")
            else:
                active.append("{} Türen".format(count))

        count = len(ToolboxHelper.getFilteredGroupMember("gGF_Sensor_Window", scope.OPEN))
        count += len(ToolboxHelper.getFilteredGroupMember("gFF_Sensor_Window", scope.OPEN))
        #count += 1 if Registry.getItemState("pToolshed_Openingcontact_Window_State") == scope.OPEN else 0
        if count > 0:
            active.append("{} Fenster".format(count))

        if len(active) > 0:
            msg = "{} offen".format(" und ".join(active))
        else:
            msg = "Alles geschlossen"

        Registry.getItem("pOther_State_Message_Security").postUpdateIfDifferent(msg)
