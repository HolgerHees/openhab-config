from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from datetime import datetime, timedelta


@rule(
    triggers = [
        GenericCronTrigger("0 1 * * * ?"),
        ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light")
    ]
)
class Main:
    def execute(self, module, input):
        state = Registry.getItemState("pOther_Manual_State_Auto_Attic_Light").intValue();
        if state not in [2,3]:
            return

        hour = datetime.now().astimezone().hour

        if state == 2:
            state = ON if hour >= 5 and hour <= 23 else OFF
        else:
            state = ON if hour >= 8 and hour <= 20 else OFF

        Registry.getItem("pMobile_Socket_7_Powered").sendCommandIfDifferent(state)
