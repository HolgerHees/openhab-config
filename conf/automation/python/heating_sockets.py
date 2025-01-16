from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.presence import PresenceHelper


@rule(
    triggers = [
        #GenericCronTrigger("0 */15 * * * ?"),
        ItemStateChangeTrigger("pGF_Livingroom_Air_Sensor_Temperature_Value"),
        ItemStateChangeTrigger("pGF_Corridor_Air_Sensor_Temperature_Value"),
        ItemStateChangeTrigger("pOther_Presence_State")
    ]
)
class LivingroomControl:
    def execute(self, module, input):
        presence_state = Registry.getItemState("pOther_Presence_State").intValue()

        if presence_state in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
            if input["event"].getItemName() == "pOther_Presence_State":
                Registry.getItem("pMobile_Socket_5_Powered").sendCommandIfDifferent(OFF)
            return

        temperature_floor = Registry.getItemState("pGF_Corridor_Air_Sensor_Temperature_Value").doubleValue()
        temperature_livingroom = Registry.getItemState("pGF_Livingroom_Air_Sensor_Temperature_Value").doubleValue()

        diff = temperature_livingroom - temperature_floor

        if diff >= 2.0:
            Registry.getItem("pMobile_Socket_5_Powered").sendCommandIfDifferent(ON)
        elif diff <= 1.5:
            Registry.getItem("pMobile_Socket_5_Powered").sendCommandIfDifferent(OFF)
        #self.logger.info("{} {} {}".format(temperature_floor, temperature_livingroom, diff))

@rule(
    triggers = [
        #GenericCronTrigger("0 */15 * * * ?"),
        ItemStateChangeTrigger("pToolshed_Sensor_Temperature_Value")
    ]
)
class ToolshedControl:
    def execute(self, module, input):
        value = input["event"].getItemState().doubleValue()
        if value >= 5.7:
            Registry.getItem("pMobile_Socket_6_Powered").sendCommandIfDifferent(OFF)
        elif value <= 5.3:
            Registry.getItem("pMobile_Socket_6_Powered").sendCommandIfDifferent(ON)
        #self.logger.info("{} {} {}".format(temperature_floor, temperature_livingroom, value))
