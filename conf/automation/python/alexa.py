from openhab import rule, Registry
from openhab.triggers import ThingStatusChangeTrigger, SystemStartlevelTrigger


@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ThingStatusChangeTrigger("amazonechocontrol:account:account1")
    ]
)
class StateMessage:
    def execute(self, module, input):
        thing = Registry.getThing("amazonechocontrol:account:account1")

        msg = "Thing: {}".format(thing.getStatusInfo().toString()) if thing.getStatus().toString() != "ONLINE" else ""
        Registry.getItem("eOther_Error_Alexa_Message").postUpdateIfDifferent(msg)
