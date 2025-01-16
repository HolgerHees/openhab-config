from openhab import rule, Registry
from openhab.triggers import ThingStatusChangeTrigger, SystemStartlevelTrigger


@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ThingStatusChangeTrigger("hue:bridge-api2:default")
    ]
)
class StateMessage:
    def execute(self, module, input):
        thing = Registry.getThing("hue:bridge-api2:default")

        msg = "Thing: {}".format(thing.getStatusInfo().toString()) if thing.getStatus().toString() != "ONLINE" else ""
        Registry.getItem("eOther_Error_Hue_Message").postUpdateIfDifferent(msg)
