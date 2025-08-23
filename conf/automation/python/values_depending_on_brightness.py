from openhab import rule, logger, Registry
from openhab.triggers import GenericCronTrigger

from shared.toolbox import ToolboxHelper

from custom.sunprotection import SunProtectionHelper
from custom.weather import WeatherHelper

from datetime import datetime, timedelta

import scope


@rule(
    triggers = [
        GenericCronTrigger("0 * * * * ?")
    ]
)
class Main:
    def execute(self, module, input):
        now = datetime.now().astimezone()
        
        cloud_cover = WeatherHelper.getCloudCoverItemState().intValue()
        light_level = WeatherHelper.getLightLevelItemState().intValue()
        
        automatic_rollershutter_state = Registry.getItemState("pOther_Automatic_State_Rollershutter").intValue()

        if automatic_rollershutter_state != SunProtectionHelper.STATE_ROLLERSHUTTER_UP:
            _up_time = Registry.getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime()
            _up_time = _up_time + timedelta(seconds=int( ( cloud_cover * 30.0 / 9.0 ) * 60 ) )

            if now.hour < 12 and now.date() == _up_time.date():
                if now >= _up_time:
                    Registry.getItem("pOther_Automatic_State_Rollershutter").postUpdate(SunProtectionHelper.STATE_ROLLERSHUTTER_UP)
                elif light_level > 0 and automatic_rollershutter_state != SunProtectionHelper.STATE_ROLLERSHUTTER_MAYBE_UP:
                    _up_time = Registry.getItemState("pOutdoor_Astro_Dawn_Time").getZonedDateTime()
                    if now >= _up_time:
                        Registry.getItem("pOther_Automatic_State_Rollershutter").postUpdate(SunProtectionHelper.STATE_ROLLERSHUTTER_MAYBE_UP)
                        
            Registry.getItem("pOther_Automatic_State_Rollershutter_Up").postUpdateIfDifferent(_up_time)
        else:
            _down_time = Registry.getItemState("pOutdoor_Astro_Dusk_Time").getZonedDateTime()
            _down_time = _down_time - timedelta(seconds=int( ( cloud_cover * 30.0 / 9.0 ) * 60 ) )
            
            if now >= _down_time:
                Registry.getItem("pOther_Automatic_State_Rollershutter").postUpdate(SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN)
            elif light_level <= 0:
                _down_time = Registry.getItemState("pOutdoor_Astro_Sunset_Time").getZonedDateTime()
                if now >= _down_time:
                    Registry.getItem("pOther_Automatic_State_Rollershutter").postUpdate(SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN)
 
            Registry.getItem("pOther_Automatic_State_Rollershutter_Down").postUpdateIfDifferent(_down_time)

        if light_level <= 0 or Registry.getItemState("pOutdoor_Astro_Sunset_Time").getZonedDateTime() < now or Registry.getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime() > now:
            Registry.getItem("pOther_Automatic_State_Outdoorlights").postUpdateIfDifferent(scope.ON)
        else:
            Registry.getItem("pOther_Automatic_State_Outdoorlights").postUpdateIfDifferent(scope.OFF)
            
        if Registry.getItemState("pOutdoor_Astro_Dusk_Time").getZonedDateTime() < now or Registry.getItemState("pOutdoor_Astro_Dawn_Time").getZonedDateTime() > now:
            Registry.getItem("pOther_Automatic_State_Solar").postUpdateIfDifferent(scope.OFF)
        else:
            Registry.getItem("pOther_Automatic_State_Solar").postUpdateIfDifferent(scope.ON)
