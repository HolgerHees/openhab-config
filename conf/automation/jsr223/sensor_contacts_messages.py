from custom.helper import rule, getGroupMemberChangeTrigger, getFilteredChildItems, postUpdateIfChanged


@rule("sensor_contact_messages.py")
class SensorContactMessagesRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("Sensor_Doors_FF")
        self.triggers += getGroupMemberChangeTrigger("Sensor_Window_FF")
        self.triggers += getGroupMemberChangeTrigger("Sensor_Window_SF")

    def execute(self, module, input):
        active = []

        count = len(getFilteredChildItems("Sensor_Doors_FF", OPEN))
        if count > 0:
            if count == 1:
                active.append(u"1 Tür")
            else:
                active.append(u"{} Türen".format(count))

        count = len(getFilteredChildItems("Sensor_Window_FF", OPEN))
        count += len(getFilteredChildItems("Sensor_Window_SF", OPEN))
        if count > 0:
            active.append(u"{} Fenster".format(count))

        if len(active) > 0:
            msg = u"{} offen".format(u" und ".join(active))
        else:
            msg = u"Alles geschlossen"

        postUpdateIfChanged("RoomStatus", msg)
