from openhab import Registry
from shared.toolbox import ToolboxHelper

from org.openhab.core.library.types import DecimalType as Java_DecimalType

import scope


class WeatherHelper:
    @staticmethod
    def isWorking():
        return Registry.getItemState("pOutdoor_WeatherStation_Is_Working") == scope.ON

    # *** TEMPERATURE ***
    @staticmethod
    def getTemperatureItemName():
        return "pOutdoor_WeatherStation_Temperature" if Registry.getItemState("pOutdoor_WeatherStation_Is_Working") == scope.ON else "pGF_Utilityroom_Heating_Temperature_Outdoor"

    @staticmethod
    def getTemperatureStableItemState(time_slot):
        return ToolboxHelper.getStableState(WeatherHelper.getTemperatureItemName(), time_slot)

    #@staticmethod
    #def getTemperature():
    #    return Registry.getItemState("pOutdoor_WeatherStation_Temperature").doubleValue() if Registry.getItemState("pOutdoor_WeatherStation_Is_Working") == ON else Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Outdoor").doubleValue()

    # *** SOLAR_POWER ***
    @staticmethod
    def _getSolarPowerItemName():
        is_working = Registry.getItemState("pOutdoor_WeatherStation_Is_Working") == scope.ON
        return [ not is_working, "pOutdoor_WeatherStation_Solar_Power" if is_working else "pOutdoor_Astro_Total_Radiation" ]

    @staticmethod
    def getSolarPowerStableItemState(time_slot):
        is_fallback, item_name = WeatherHelper._getSolarPowerItemName()
        value = ToolboxHelper.getStableState(item_name, time_slot)
        if is_fallback:
            octa = Registry.getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
            value = Java_DecimalType(value.doubleValue() * ( 1.0 / octa ))
        return value

    # *** LIGHT_LEVEL ***
    @staticmethod
    def _getLightLevelItemName():
        is_working = Registry.getItemState("pOutdoor_WeatherStation_Is_Working") == scope.ON
        return [ not is_working, "pOutdoor_WeatherStation_Light_Level" if is_working else "pOutdoor_Astro_Light_Level" ]

    @staticmethod
    def getLightLevelStableItemState(time_slot):
        is_fallback, item_name = WeatherHelper._getLightLevelItemName()
        value = ToolboxHelper.getStableState(item_name, time_slot)
        if is_fallback:
            octa = Registry.getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
            value = Java_DecimalType(value.doubleValue() * ( 1.0 / octa ))
        return value

    @staticmethod
    def getLightLevelItemState():
        is_fallback, item_name = WeatherHelper._getLightLevelItemName()
        value = Registry.getItemState(item_name)
        if is_fallback:
            octa = Registry.getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
            value = Java_DecimalType(value.intValue() * ( 1.0 / octa ))
        return value

    # *** CLOUD_COVER ***
    @staticmethod
    def getCloudCoverItemState():
        return Registry.getItemState("pOutdoor_WeatherStation_Cloud_Cover") if Registry.getItemState("pOutdoor_WeatherStation_Is_Working") == scope.ON else Registry.getItemState("pOutdoor_Weather_Current_Cloud_Cover")
