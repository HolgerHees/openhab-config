from shared.helper import rule, getGroupMemberChangeTrigger, ItemStateChangeTrigger, getFilteredChildItems, postUpdateIfChanged, getItemState


@rule()
class StateMessageSecurity:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Doors")
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gFF_Sensor_Window")
        self.triggers += [ItemStateChangeTrigger("pToolshed_Openingcontact_Door_State")]
        #self.triggers += [ItemStateChangeTrigger("pToolshed_Openingcontact_Window_State")]

    def execute(self, module, input):
        active = []

        count = len(getFilteredChildItems("gGF_Sensor_Doors", OPEN))
        count += 1 if getItemState("pToolshed_Openingcontact_Door_State") == OPEN else 0
        if count > 0:
            if count == 1:
                active.append(u"1 Tür")
            else:
                active.append(u"{} Türen".format(count))

        count = len(getFilteredChildItems("gGF_Sensor_Window", OPEN))
        count += len(getFilteredChildItems("gFF_Sensor_Window", OPEN))
        #count += 1 if getItemState("pToolshed_Openingcontact_Window_State") == OPEN else 0
        if count > 0:
            active.append(u"{} Fenster".format(count))

        if len(active) > 0:
            msg = u"{} offen".format(u" und ".join(active))
        else:
            msg = u"Alles geschlossen"

        postUpdateIfChanged("pOther_State_Message_Security", msg)
