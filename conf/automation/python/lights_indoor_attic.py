from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from datetime import datetime, timedelta

import scope


hour = datetime.now().astimezone().hour
print(hour)

@rule(
    triggers = [
        GenericCronTrigger("0 0 * * * ?"),
        ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light")
    ]
)
class Main:
    def execute(self, module, input):
        state = Registry.getItemState("pOther_Manual_State_Auto_Attic_Light").intValue();
        if state not in [1,2]:
            return

        hour = datetime.now().astimezone().hour

        if state == 1:
            state = scope.ON if hour >= 5 and hour <= 22 else scope.OFF # 05:00 - 22:59 (18 Stunden)
        else:
            state = scope.ON if hour >= 8 and hour <= 19 else scope.OFF # 08:00 - 19:59 (12 Stunden)

        Registry.getItem("pMobile_Socket_7_Powered").sendCommandIfDifferent(state)
