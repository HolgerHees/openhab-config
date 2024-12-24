from shared.helper import getItemState, getStableItemState
from shared.actions import Transformation

from org.openhab.core.library.types import OnOffType


class WeatherHelper:
    @staticmethod
    def isWorking():
        return getItemState("pOutdoor_WeatherStation_Is_Working") == OnOffType.ON

    # *** TEMPERATURE ***
    @staticmethod
    def getTemperatureItemName():
        return "pOutdoor_WeatherStation_Temperature" if getItemState("pOutdoor_WeatherStation_Is_Working") == OnOffType.ON else "pGF_Utilityroom_Heating_Temperature_Outdoor"

    @staticmethod
    def getTemperatureStableItemState(now, checkTimeRange):
        return getStableItemState(now, WeatherHelper.getTemperatureItemName(), checkTimeRange)

    #@staticmethod
    #def getTemperature():
    #    return getItemState("pOutdoor_WeatherStation_Temperature").doubleValue() if getItemState("pOutdoor_WeatherStation_Is_Working") == ON else getItemState("pGF_Utilityroom_Heating_Temperature_Outdoor").doubleValue()

    # *** SOLAR_POWER ***
    @staticmethod
    def _getSolarPowerItemName():
        is_working = getItemState("pOutdoor_WeatherStation_Is_Working") == OnOffType.ON
        return [ not is_working, "pOutdoor_WeatherStation_Solar_Power" if is_working else "pOutdoor_Astro_Total_Radiation" ]

    @staticmethod
    def getSolarPowerStableItemState(now, checkTimeRange):
        is_fallback, item_name = WeatherHelper._getSolarPowerItemName()
        value = getStableItemState(now, item_name, checkTimeRange)
        if is_fallback:
            octa = getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
            value = value * ( 1.0 / octa )
        return value

    # *** LIGHT_LEVEL ***
    @staticmethod
    def _getLightLevelItemName():
        is_working = getItemState("pOutdoor_WeatherStation_Is_Working") == OnOffType.ON
        return [ not is_working, "pOutdoor_WeatherStation_Light_Level" if is_working else "pOutdoor_Astro_Light_Level" ]

    @staticmethod
    def getLightLevelStableItemState(now, checkTimeRange):
        is_fallback, item_name = WeatherHelper._getLightLevelItemName()
        value = getStableItemState(now, item_name, checkTimeRange)
        if is_fallback:
            octa = getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
            value = value * ( 1.0 / octa )
        return value

    @staticmethod
    def getLightLevelItemState():
        is_fallback, item_name = WeatherHelper._getLightLevelItemName()
        value = getItemState(item_name).intValue()
        if is_fallback:
            octa = getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
            value = value * ( 1.0 / octa )
        return value

    # *** CLOUD_COVER ***
    @staticmethod
    def getCloudCoverItemState():
        return getItemState("pOutdoor_WeatherStation_Cloud_Cover").intValue() if getItemState("pOutdoor_WeatherStation_Is_Working") == OnOffType.ON else getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
