from java.time import ZonedDateTime

from shared.helper import rule, getItemState, sendCommandIfChanged
from shared.triggers import CronTrigger, ItemStateChangeTrigger


@rule()
class LightsIndoorAttic:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 1 * * * ?"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light")
        ]

    def execute(self, module, input):
        state = getItemState("pOther_Manual_State_Auto_Attic_Light").intValue();
        if state not in [2,3]:
            return

        hour = ZonedDateTime.now().getHour()

        if state == 2:
            state = ON if hour >= 5 and hour <= 23 else OFF
        else:
            state = ON if hour >= 8 and hour <= 20 else OFF

        sendCommandIfChanged("pMobile_Socket_7_Powered", state)
