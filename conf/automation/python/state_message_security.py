from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger, GroupStateChangeTrigger

from shared.toolbox import ToolboxHelper

import scope


@rule(
    triggers = [
        GroupStateChangeTrigger("gGF_Sensor_Doors"),
        GroupStateChangeTrigger("gGF_Sensor_Window"),
        GroupStateChangeTrigger("gFF_Sensor_Window"),
        ItemStateChangeTrigger("pToolshed_Openingcontact_Door_State")
    ]
)
class Main:
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
