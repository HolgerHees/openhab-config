from shared.helper import rule, getGroupMemberChangeTrigger, ItemStateChangeTrigger, getFilteredChildItems, postUpdateIfChanged, getItemState


@rule()
class StateMessageNotification:
    def __init__(self):
        self.triggers = []
        self.triggers += [
            ItemStateChangeTrigger("pOther_Manual_State_Security_Notify"),
            ItemStateChangeTrigger("pOther_Manual_State_Air_Thoroughly_Notify"),
            ItemStateChangeTrigger("pOther_Manual_State_Calendar_Event_Notify")
        ]

    def execute(self, module, input):
        active = []

        active.append( "s" if getItemState("pOther_Manual_State_Security_Notify") == ON else u"s\u0336")

        state = getItemState("pOther_Manual_State_Air_Thoroughly_Notify").intValue()
        if state == 0:
            active.append(u"p\u0336a\u0336")
        elif state == 1:
            active.append(u"pa\u0336")
        elif state == 2:
            active.append(u"p\u0336a")
        elif state == 3:
            active.append(u"pa")

        state = getItemState("pOther_Manual_State_Calendar_Event_Notify").intValue()
        if state == 0:
            active.append(u"p\u0336a\u0336")
        elif state == 1:
            active.append(u"pa\u0336")
        elif state == 2:
            active.append(u"p\u0336a")
        elif state == 3:
            active.append(u"pa")

        postUpdateIfChanged("pOther_State_Message_Notifications", "-".join(active))
