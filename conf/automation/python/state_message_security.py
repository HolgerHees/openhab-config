from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper


@rule()
class Main:
    def buildTriggers(self):
        triggers = []
        triggers += ToolboxHelper.getGroupMemberTrigger(ItemStateChangeTrigger, "gGF_Sensor_Doors")
        triggers += ToolboxHelper.getGroupMemberTrigger(ItemStateChangeTrigger, "gGF_Sensor_Window")
        triggers += ToolboxHelper.getGroupMemberTrigger(ItemStateChangeTrigger, "gFF_Sensor_Window")
        triggers += [ItemStateChangeTrigger("pToolshed_Openingcontact_Door_State")]
        #triggers += [ItemStateChangeTrigger("pToolshed_Openingcontact_Window_State")]
        return triggers

    def execute(self, module, input):
        active = []

        count = len(ToolboxHelper.getFilteredGroupMember("gGF_Sensor_Doors", OPEN))
        count += 1 if Registry.getItemState("pToolshed_Openingcontact_Door_State") == OPEN else 0
        if count > 0:
            if count == 1:
                active.append("1 Tür")
            else:
                active.append("{} Türen".format(count))

        count = len(ToolboxHelper.getFilteredGroupMember("gGF_Sensor_Window", OPEN))
        count += len(ToolboxHelper.getFilteredGroupMember("gFF_Sensor_Window", OPEN))
        #count += 1 if Registry.getItemState("pToolshed_Openingcontact_Window_State") == OPEN else 0
        if count > 0:
            active.append("{} Fenster".format(count))

        if len(active) > 0:
            msg = "{} offen".format(" und ".join(active))
        else:
            msg = "Alles geschlossen"

        Registry.getItem("pOther_State_Message_Security").postUpdateIfDifferent(msg)
