from shared.helper import getItemState
from shared.actions import Transformation

from org.openhab.core.library.types import OnOffType


class WateringHelper:
    STATE_WATERING_INACTIVE = -1

    STATE_WATERING_NOW = 4
    STATE_WATERING_MAYBE = 3
    STATE_WATERING_OPTIMAL = 2
    STATE_WATERING_WET = 1

    @staticmethod
    def isActive(device_name):
        return getItemState("p" + device_name  + "_Switch") == OnOffType.ON

    @staticmethod
    def getHumidity(device_name):
        return getItemState("p" + device_name  + "_Soil_Humidity").intValue()

    @staticmethod
    def getState(device_name, value = None):
        min_value = getItemState("p" + device_name  + "_Min_Soil_Humidity").intValue()
        max_value = getItemState("p" + device_name  + "_Max_Soil_Humidity").intValue()
        if value is None:
            value = WateringHelper.getHumidity(device_name)

        if value < min_value:
            return WateringHelper.STATE_WATERING_NOW

        if value < min_value + ( ( max_value - min_value ) / 2 ):
            return WateringHelper.STATE_WATERING_MAYBE

        if value < max_value:
            return WateringHelper.STATE_WATERING_OPTIMAL

        return WateringHelper.STATE_WATERING_WET

    @staticmethod
    def getStateInfo(value):
        return Transformation.transform("MAP", "gardena_state.map", str(value) )
