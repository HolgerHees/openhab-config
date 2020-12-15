from shared.helper import rule, getGroupMemberChangeTrigger, getFilteredChildItems, postUpdateIfChanged


@rule("sensor_contact_messages.py")
class SensorContactMessagesRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Doors")
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gFF_Sensor_Window")

    def execute(self, module, input):
        active = []

        count = len(getFilteredChildItems("gGF_Sensor_Doors", OPEN))
        if count > 0:
            if count == 1:
                active.append(u"1 Tür")
            else:
                active.append(u"{} Türen".format(count))

        count = len(getFilteredChildItems("gGF_Sensor_Window", OPEN))
        count += len(getFilteredChildItems("gFF_Sensor_Window", OPEN))
        if count > 0:
            active.append(u"{} Fenster".format(count))

        if len(active) > 0:
            msg = u"{} offen".format(u" und ".join(active))
        else:
            msg = u"Alles geschlossen"

        postUpdateIfChanged("pOther_State_Message_Room", msg)
