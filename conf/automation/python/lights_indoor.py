from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, ItemStateCondition

from custom.presence import PresenceHelper

from datetime import datetime, timedelta

import scope


@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Automatic_State_Outdoorlights", state=scope.ON),
        ItemStateChangeTrigger("pOther_Presence_State", state=PresenceHelper.STATE_AWAY)
    ],
    conditions = [
        ItemStateCondition("pOther_Manual_State_Auto_Lighting", operator="=", state=scope.ON ),
        ItemStateCondition("pOther_Automatic_State_Outdoorlights", operator="=", state=scope.ON ),
        ItemStateCondition("pOther_Presence_State", operator="=", state=PresenceHelper.STATE_AWAY )
    ]
)
class AwayEvening:
    def execute(self, module, input):
        now = datetime.now().astimezone()
        end_time = now.replace(hour=21, minute=30)
        if end_time < now:
            Registry.getItem("pGF_Corridor_Light_Hue_Color").sendCommand(30)
            Registry.getItem("pGF_Livingroom_Light_Hue4_Color").sendCommand(30)


@rule(
    triggers = [
        GenericCronTrigger("0 0 22 * * ?")
    ],
    conditions = [
        ItemStateCondition("pOther_Manual_State_Auto_Lighting", operator="=", state=scope.ON ),
        ItemStateCondition("pOther_Presence_State", operator="=", state=PresenceHelper.STATE_AWAY )
    ]
)
class HolidayGoSleeping:
    def execute(self, module, input):
        Registry.getItem("pGF_Corridor_Light_Hue_Color").sendCommand(scope.OFF)
        Registry.getItem("pGF_Livingroom_Light_Hue4_Color").sendCommand(scope.OFF)
        Registry.getItem("pGF_Corridor_Light_Ceiling_Powered").sendCommand(scope.ON)


@rule(
    triggers = [
        GenericCronTrigger("0 30 22 * * ?")
    ],
    conditions = [
        ItemStateCondition("pOther_Manual_State_Auto_Lighting", operator="=", state=scope.ON ),
        ItemStateCondition("pOther_Presence_State", operator="=", state=PresenceHelper.STATE_AWAY )
    ]
)
class HolidayNight:
    def execute(self, module, input):
        Registry.getItem("pGF_Corridor_Light_Ceiling_Powered").sendCommand(scope.OFF)
