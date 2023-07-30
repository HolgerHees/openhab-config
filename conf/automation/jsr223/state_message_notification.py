from shared.helper import rule, getGroupMemberChangeTrigger, ItemStateChangeTrigger, getFilteredChildItems, postUpdateIfChanged, getItemState

from custom.flags import FlagHelper


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

        flags = getItemState("pOther_Manual_State_Air_Thoroughly_Notify").intValue()
        if FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags) and FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags):
            active.append(u"pa")
        elif FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags):
            active.append(u"pa\u0336")
        elif FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags):
            active.append(u"p\u0336a")
        elif FlagHelper.hasFlag(FlagHelper.OFF, flags):
            active.append(u"p\u0336a\u0336")
        else:
            self.log.error("Unknown flag {}".format(flags))

        flags = getItemState("pOther_Manual_State_Calendar_Event_Notify").intValue()
        if FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags) and FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags):
            active.append(u"pa")
        elif FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags):
            active.append(u"pa\u0336")
        elif FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags):
            active.append(u"p\u0336a")
        elif FlagHelper.hasFlag(FlagHelper.OFF, flags):
            active.append(u"p\u0336a\u0336")
        else:
            self.log.error("Unknown flag {}".format(flags))

        postUpdateIfChanged("pOther_State_Message_Notifications", ",".join(active))
