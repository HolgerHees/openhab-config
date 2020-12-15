from shared.helper import rule, getGroupMemberChangeTrigger, sendNotification, getItem, getItemState


@rule("sensor_contact_notification.py")
class SensorContactNotificationRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Doors")
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gFF_Sensor_Window")
        self.timer = None

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Notify") == ON:
            itemName = input['event'].getItemName()
            item = getItem(itemName)

            group = itemName
            if group.startswith("Door"):
                group = u"Tür"
            else:
                group = u"Fenster"

            sendNotification(group, u"{} {}".format(item.getLabel(),input['event'].getItemState().toString()))
