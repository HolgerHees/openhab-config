from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger


@rule(
    triggers = [
        GenericCronTrigger("0 * * * * ?")
    ]
)
class Message:
    def execute(self, module, input):
        items = Registry.getItem("eOther_Error").getAllMembers()
        for item in items:
            if item.getState() != NULL and len(item.getState().toString()) > 0:
                self.logger.info("STATE: {} - {}".format(item.getLabel(), item.getState()))
