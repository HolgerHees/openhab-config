from shared.helper import rule, getItem
from shared.triggers import CronTrigger


@rule("error.py")
class ErrorMessageRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 * * * * ?")
        ]
        self.check()

    def check(self):
        items = getItem("eOther_Error").getAllMembers()
        for item in items:
            #self.log.info(u"{}".format(item.getLabel()))
            #self.log.info(u"{}".format(item.getState() == NULL))
            if item.getState() != NULL and len(item.getState().toString()) > 0:
                self.log.info(u"STATE: {} - {}".format(item.getLabel(), item.getState()))
            #else:
            #    self.log.info(u"STATE: {} - {}".format(item.getLabel(), "test"))

    def execute(self, module, input):
        self.check()
