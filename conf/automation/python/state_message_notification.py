from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from custom.flags import FlagHelper


@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Manual_State_Security_Notify"),
        ItemStateChangeTrigger("pOther_Manual_State_Air_Thoroughly_Notify"),
        ItemStateChangeTrigger("pOther_Manual_State_Calendar_Event_Notify")
    ]
)
class Main:
    def execute(self, module, input):
        active = []

        active.append( "s" if Registry.getItemState("pOther_Manual_State_Security_Notify") == ON else "s\u0336")

        flags = Registry.getItemState("pOther_Manual_State_Air_Thoroughly_Notify").intValue()
        if FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags) and FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags):
            active.append("pa")
        elif FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags):
            active.append("pa\u0336")
        elif FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags):
            active.append("p\u0336a")
        elif FlagHelper.hasFlag(FlagHelper.OFF, flags):
            active.append("p\u0336a\u0336")
        else:
            self.logger.error("Unknown flag {}".format(flags))

        flags = Registry.getItemState("pOther_Manual_State_Calendar_Event_Notify").intValue()
        if FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags) and FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags):
            active.append("pa")
        elif FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags):
            active.append("pa\u0336")
        elif FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags):
            active.append("p\u0336a")
        elif FlagHelper.hasFlag(FlagHelper.OFF, flags):
            active.append("p\u0336a\u0336")
        else:
            self.logger.error("Unknown flag {}".format(flags))

        Registry.getItem("pOther_State_Message_Notifications").postUpdateIfDifferent(",".join(active))
