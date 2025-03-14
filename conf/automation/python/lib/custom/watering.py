from openhab import Registry
from openhab.actions import Transformation

from org.openhab.core.library.types import OnOffType as Java_OnOffType


class WateringHelper:
    STATE_WATERING_INACTIVE = -1

    STATE_WATERING_NOW = 4
    STATE_WATERING_MAYBE = 3
    STATE_WATERING_OPTIMAL = 2
    STATE_WATERING_WET = 1

    STATE_CONTROL_OFF = 0
    STATE_CONTROL_START_NOW = 1
    STATE_CONTROL_START_MORNING = 2
    STATE_CONTROL_START_EVENING = 3

    @staticmethod
    def getFactor(device_name):
        factor = 1.0
        if device_name is not None and WateringHelper.isActive(device_name):
            state = WateringHelper.getState(device_name)
            if state in [WateringHelper.STATE_WATERING_OPTIMAL,WateringHelper.STATE_WATERING_WET]:
                factor = 0.0
            elif state in [WateringHelper.STATE_WATERING_MAYBE]:
                factor = 0.5
            elif state in [WateringHelper.STATE_WATERING_NOW]:
                factor = 1.0
        return factor

    @staticmethod
    def isActive(device_name):
        return Registry.getItemState("p" + device_name  + "_Switch") == Java_OnOffType.ON

    @staticmethod
    def getHumidity(device_name):
        return Registry.getItemState("p" + device_name  + "_Soil_Humidity").intValue()

    @staticmethod
    def getState(device_name, value = None):
        plant_tresholds = Registry.getItemState("p" + device_name  + "_Tresholds").toString()
        plant_tresholds = plant_tresholds.split(",")

        if len(plant_tresholds) != 3:
            return None

        try:
            plant_tresholds = [int(numeric_string) for numeric_string in plant_tresholds]
        except ValueError:
            return None

        if value is None:
            value = WateringHelper.getHumidity(device_name)

        if value <= int(plant_tresholds[0]):
            return WateringHelper.STATE_WATERING_NOW

        if value <= int(plant_tresholds[1]):
            return WateringHelper.STATE_WATERING_MAYBE

        if value <= int(plant_tresholds[2]):
            return WateringHelper.STATE_WATERING_OPTIMAL

        return WateringHelper.STATE_WATERING_WET

    @staticmethod
    def getStateInfo(value):
        return Transformation.transform("MAP", "gardena_state.map", str(value) )

