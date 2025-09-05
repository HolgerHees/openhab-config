from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger, ThingStatusChangeTrigger, SystemStartlevelTrigger

from custom.watering import WateringHelper


@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ThingStatusChangeTrigger("gardena:sensor:default")
    ]
)
class State:
    def execute(self, module, input):
        thing = Registry.getThing("gardena:account:default")
        status = thing.getStatus()

        Registry.getItem("eOther_Error_Gardena_Message").postUpdateIfDifferent("Thing: {}".format(thing.getStatusInfo().toString()) if status.toString() != "ONLINE" else "")


@rule()
class BatteryDetail:
    def __init__(self):
        self.sensor_device_map = {}

    def buildTriggers(self):
        triggers = [SystemStartlevelTrigger(80)]
        for item in Registry.getItem("eOther_Plant_Sensor_Devices").getMembers():
            name = item.getName()[1:]
            triggers.append(ItemStateChangeTrigger( "p" + name + "_Battery_Level"))
            self.sensor_device_map["p" + name + "_Battery_Level"] = name
        return triggers

    def execute(self, module, input):
        minLevel = 100
        for _device_name in self.sensor_device_map.values():
            if not WateringHelper.isActive(_device_name):
                continue

            value = Registry.getItemState("p" + _device_name + "_Battery_Level").intValue()
            if value < minLevel:
                minLevel = value

        if minLevel < 30:
            Registry.getItem("pOther_Plant_Sensor_State_Device_Info").postUpdateIfDifferent("Batterie")
        else:
            Registry.getItem("pOther_Plant_Sensor_State_Device_Info").postUpdateIfDifferent("Alles ok")

@rule()
class MessagesDetail:
    def __init__(self):
        self.sensor_devices = []
        self.sensor_device_map = {}

    def buildTriggers(self):
        triggers = []
        for item in Registry.getItem("eOther_Plant_Sensor_Devices").getMembers():
            name = item.getName()[1:]
            for item_suffix in ["_Switch","_Soil_Temperature","_Soil_Humidity", '_Tresholds']:
                triggers.append(ItemStateChangeTrigger( "p" + name + item_suffix))
                self.sensor_device_map["p" + name + item_suffix] = name
            self.sensor_devices.append(name)

            #self.check(name)
        return triggers

    # 50 => Leicht feucht
    # 80 => Nass

    def getInfo(self, value):
        if value <= 35:
            return "Trocken"

        if value <= 55:
            return "Leicht Feucht"

        if value <= 80:
            return "Feucht"

        return "Nass"

    def check(self, device_name):
        if not WateringHelper.isActive(device_name):
            state_level = WateringHelper.STATE_WATERING_INACTIVE
            info_msg = WateringHelper.getStateInfo(state_level)
        else:
            humidity_value = WateringHelper.getHumidity(device_name)
            state_level = WateringHelper.getState(device_name, humidity_value)
            if state_level is None:
                state_level = WateringHelper.STATE_WATERING_INACTIVE
                info_msg = "Fehlerhafte Schwellenwerte"
            else:
                state_msg = WateringHelper.getStateInfo(state_level)

                temperatur_value = Registry.getItemState("p" + device_name  + "_Soil_Temperature").intValue()
                info_msg = "{}, {}, {}°C, {}%".format( self.getInfo(humidity_value), state_msg, temperatur_value, humidity_value)

        Registry.getItem("p" + device_name  + "_State").postUpdateIfDifferent(state_level)
        Registry.getItem("p" + device_name + "_Msg").postUpdateIfDifferent(info_msg )

        state_level = WateringHelper.STATE_WATERING_INACTIVE
        for _device_name in self.sensor_devices:
            if not WateringHelper.isActive(_device_name):
                continue

            _state_level = WateringHelper.getState(_device_name)
            if _state_level > state_level:
                state_level = _state_level

        Registry.getItem("pOther_Plant_Sensor_State_Watering_Info").postUpdateIfDifferent(state_level )

    def execute(self, module, input):
        if input['event'].getType() == "StartlevelEvent":
            for device_name in self.sensor_devices:
                self.check(device_name)
        else:
            device_name = self.sensor_device_map[input["event"].getItemName()]
            self.check(device_name)

