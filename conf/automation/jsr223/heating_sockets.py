from shared.helper import rule, getItemState, sendCommandIfChanged
from shared.triggers import CronTrigger, ItemStateChangeTrigger
from custom.presence import PresenceHelper


@rule()
class HeatingSocketsLivingroomControl:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0 */15 * * * ?"),
            ItemStateChangeTrigger("pGF_Livingroom_Air_Sensor_Temperature_Value"),
            ItemStateChangeTrigger("pGF_Corridor_Air_Sensor_Temperature_Value"),
            ItemStateChangeTrigger("pOther_Presence_State")
        ]

    def execute(self, module, input):
        presentState = getItemState("pOther_Presence_State").intValue()

        if presentState in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
            if input["event"].getItemName() == "pOther_Presence_State":
                sendCommandIfChanged("pMobile_Socket_5_Powered", OFF)
            return

        temperatureFloor = getItemState("pGF_Corridor_Air_Sensor_Temperature_Value").doubleValue()
        temperatureLivingroom = getItemState("pGF_Livingroom_Air_Sensor_Temperature_Value").doubleValue()

        diff = temperatureLivingroom - temperatureFloor

        if diff >= 2.0:
            sendCommandIfChanged("pMobile_Socket_5_Powered", ON)
        elif diff <= 1.5:
            sendCommandIfChanged("pMobile_Socket_5_Powered", OFF)
        #self.log.info("{} {} {}".format(temperatureFloor, temperatureLivingroom, diff))

@rule()
class HeatingSocketsToolshedControl:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0 */15 * * * ?"),
            ItemStateChangeTrigger("pToolshed_Sensor_Temperature_Value")
        ]

    def execute(self, module, input):
        value = input["event"].getItemState().doubleValue()
        if value >= 5.7:
            sendCommandIfChanged("pMobile_Socket_6_Powered", OFF)
        elif value <= 5.3:
            sendCommandIfChanged("pMobile_Socket_6_Powered", ON)
        #self.log.info("{} {} {}".format(temperatureFloor, temperatureLivingroom, value))
