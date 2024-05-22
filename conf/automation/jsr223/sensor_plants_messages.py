from shared.helper import rule, getItemState, postUpdateIfChanged, getThing, getItem, startTimer
from shared.triggers import ItemStateChangeTrigger, ThingStatusChangeTrigger
from custom.watering import WateringHelper


@rule()
class SensorPlantsState:
    def __init__(self):
        self.triggers = [
            ThingStatusChangeTrigger("gardena:sensor:default")
        ]

        startTimer(self.log, 5, self.check)

    def check(self):
        thing = getThing("gardena:account:default")
        status = thing.getStatus()

        if status.toString() != "ONLINE":
            info = thing.getStatusInfo()
            postUpdateIfChanged("eOther_Error_Gardena_Message", "Thing: {}".format(info.toString()))
        else:
            postUpdateIfChanged("eOther_Error_Gardena_Message","")

    def execute(self, module, input):
        self.check()

@rule()
class SensorPlantsBatteryDetail:
    def __init__(self):
        triggers = []

        self.sensor_device_map = {}
        for item in getItem("eOther_Plant_Sensor_Devices").getMembers():
            name = item.getName()[1:]

            #self.log.info(name)

            triggers.append(ItemStateChangeTrigger( "p" + name + "_Batterie_Level"))

            self.sensor_device_map["p" + name + "_Batterie_Level"] = name

        self.triggers = triggers

        self.check()

    def check(self):
        minLevel = 100
        for _device_name in self.sensor_device_map.values():
            if not WateringHelper.isActive(_device_name):
                continue

            value = getItemState("p" + _device_name + "_Batterie_Level").intValue()
            if value < minLevel:
                minLevel = value

        if minLevel < 30:
            postUpdateIfChanged("pOther_Plant_Sensor_State_Device_Info", "Batterie")
        else:
            postUpdateIfChanged("pOther_Plant_Sensor_State_Device_Info", "Alles ok")

    def execute(self, module, input):
        self.check()

@rule()
class SensorPlantsMessagesDetail:
    def __init__(self):
        triggers = []

        self.sensor_devices = []
        self.sensor_device_map = {}
        for item in getItem("eOther_Plant_Sensor_Devices").getMembers():
            name = item.getName()[1:]
            for item_suffix in ["_Switch","_Soil_Temperature","_Soil_Humidity"]:
                triggers.append(ItemStateChangeTrigger( "p" + name + item_suffix))
                self.sensor_device_map["p" + name + item_suffix] = name

            self.sensor_devices.append(name)

        self.triggers = triggers

    def getInfo(self, value):
        if value < 10:
            return u"Trocken"

        if value < 50:
            return u"Leicht Feucht"

        if value < 80:
            return u"Feucht"

        return u"Nass"

    def execute(self, module, input):
        device_name = self.sensor_device_map[input["event"].getItemName()]

        if not WateringHelper.isActive(device_name):
            state_level = WateringHelper.STATE_WATERING_INACTIVE
            info_msg = WateringHelper.getStateInfo(state_level)
        else:
            humidity_value = WateringHelper.getHumidity(device_name)
            state_level = WateringHelper.getState(device_name, humidity_value)
            state_msg = WateringHelper.getStateInfo(state_level)

            temperatur_value = getItemState("p" + device_name  + "_Soil_Temperature").intValue()
            info_msg = u"{}, {}, {}°C, {}%".format( self.getInfo(humidity_value), state_msg, temperatur_value, humidity_value)

        postUpdateIfChanged("p" + device_name  + "_State", state_level)
        postUpdateIfChanged("p" + device_name + "_Msg", info_msg )

        state_level = WateringHelper.STATE_WATERING_INACTIVE
        for _device_name in self.sensor_devices:
            if not WateringHelper.isActive(_device_name):
                continue

            _state_level = WateringHelper.getState(_device_name)
            if _state_level > state_level:
                state_level = _state_level

        postUpdateIfChanged("pOther_Plant_Sensor_State_Watering_Info", state_level )
