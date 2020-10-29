from shared.helper import rule, getGroupMemberChangeTrigger, sendNotification, getItem, getItemState


@rule("sensor_contact_notification.py")
class SensorContactNotificationRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("Sensor_Doors_FF")
        self.triggers += getGroupMemberChangeTrigger("Sensor_Window_FF")
        self.triggers += getGroupMemberChangeTrigger("Sensor_Window_SF")
        self.timer = None

    def execute(self, module, input):
        if getItemState("State_Notify") == ON:
            itemName = input['event'].getItemName()
            item = getItem(itemName)

            group = itemName
            if group.startswith("Door"):
                group = u"Tür"
            else:
                group = u"Fenster"

            sendNotification(group, u"{} {}".format(item.getLabel(),input['event'].getItemState().toString()))
