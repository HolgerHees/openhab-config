from shared.helper import rule, getGroupMemberChangeTrigger, ItemStateChangeTrigger, getFilteredChildItems, postUpdateIfChanged, getItemState


@rule("state_message_notification.py")
class StateMessageNotificationRule:
    def __init__(self):
        self.triggers = []
        self.triggers += [
            ItemStateChangeTrigger("pOther_Manual_State_Security_Notify"),
            ItemStateChangeTrigger("pOther_Manual_State_Air_Thoroughly_Notify"),
            ItemStateChangeTrigger("pOther_Manual_State_Calendar_Event_Notify")
        ]

    def execute(self, module, input):
        active = []

        active.append( "S" if getItemState("pOther_Manual_State_Security_Notify") == ON else "X")

        state = getItemState("pOther_Manual_State_Air_Thoroughly_Notify").intValue()
        if state == 0:
            active.append("X")
        elif state == 1:
            active.append("P")
        elif state == 2:
            active.append("A")
        elif state == 3:
            active.append("PA")

        state = getItemState("pOther_Manual_State_Calendar_Event_Notify").intValue()
        if state == 0:
            active.append("X")
        elif state == 1:
            active.append("P")
        elif state == 2:
            active.append("A")
        elif state == 3:
            active.append("PA")

        postUpdateIfChanged("pOther_State_Message_Notifications", "-".join(active))
