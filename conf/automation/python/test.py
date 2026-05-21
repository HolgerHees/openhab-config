import scope
from openhab.triggers import ItemStateChangeTrigger
from openhab import rule, Registry

@rule(
    triggers = [
        ItemStateChangeTrigger("TestItem"),
    ]
)
class TabletScreen:
    def execute(self, module, input):
        print(input["event"])

scope.events.postUpdate(Registry.getItem("TestItem"), 2, None)
