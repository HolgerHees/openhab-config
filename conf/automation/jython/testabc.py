from shared.helper import rule, postUpdateIfChanged, getThing, startTimer
from shared.triggers import ThingStatusChangeTrigger

@rule()
class JythonTest:
    def __init__(self):
        self.triggers = [
        ]

    def execute(self, module, input):
        self.log.info("triggered")
