from java.time import ZonedDateTime
from java.time.format import DateTimeFormatter

from shared.helper import rule, getItemState, itemStateNewerThen, itemStateOlderThen, postUpdateIfChanged, postUpdate
from shared.triggers import CronTrigger
from custom.sunprotection import SunProtectionHelper
from custom.weather import WeatherHelper


@rule()
class ValuesDependingOnBrightness:
    def __init__(self):
        self.triggers = [CronTrigger("0 * * * * ?")]
#        self.triggers = [CronTrigger("*/15 * * * * ?")]

    def execute(self, module, input):
        now = ZonedDateTime.now()
        
        cloudCover = WeatherHelper.getCloudCoverItemState()
        lightLevel = WeatherHelper.getLightLevelItemState()
        
        automaticRollershutterState = getItemState("pOther_Automatic_State_Rollershutter").intValue()
        
        if automaticRollershutterState != SunProtectionHelper.STATE_ROLLERSHUTTER_UP:
            _upTime = getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime()
            _upTime = _upTime.plusSeconds( int( ( cloudCover * 30.0 / 9.0 ) * 60 ) )

            if now.getHour() < 12 and now.toLocalDate().isEqual(_upTime.toLocalDate()):               
                if now.isAfter(_upTime) or now.isEqual(_upTime):
                    postUpdate("pOther_Automatic_State_Rollershutter", SunProtectionHelper.STATE_ROLLERSHUTTER_UP)
                elif lightLevel > 0 and automaticRollershutterState != SunProtectionHelper.STATE_ROLLERSHUTTER_MAYBE_UP:
                    _upTime = getItemState("pOutdoor_Astro_Dawn_Time").getZonedDateTime()
                    if now.isAfter(_upTime) or now.isEqual(_upTime):
                        postUpdate("pOther_Automatic_State_Rollershutter", SunProtectionHelper.STATE_ROLLERSHUTTER_MAYBE_UP)
                        
            postUpdateIfChanged("pOther_Automatic_State_Rollershutter_Up", _upTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")) )
        else:
            _downTime = getItemState("pOutdoor_Astro_Dusk_Time").getZonedDateTime()
            _downTime = _downTime.minusSeconds( int( ( cloudCover * 30.0 / 9.0 ) * 60 ) )
            
            if now.isAfter(_downTime) or now.isEqual(_downTime):
                postUpdate("pOther_Automatic_State_Rollershutter", SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN)
            elif lightLevel <= 0:
                _downTime = getItemState("pOutdoor_Astro_Sunset_Time").getZonedDateTime()
                if now.isAfter(_downTime) or now.isEqual(_downTime):
                    postUpdate("pOther_Automatic_State_Rollershutter", SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN)
 
            postUpdateIfChanged("pOther_Automatic_State_Rollershutter_Down", _downTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")) )

        if lightLevel <= 0 or itemStateOlderThen("pOutdoor_Astro_Sunset_Time", now) or itemStateNewerThen("pOutdoor_Astro_Sunrise_Time", now):
            postUpdateIfChanged("pOther_Automatic_State_Outdoorlights", ON)
        else:
            postUpdateIfChanged("pOther_Automatic_State_Outdoorlights", OFF)
            
        if itemStateOlderThen("pOutdoor_Astro_Dusk_Time", now) or itemStateNewerThen("pOutdoor_Astro_Dawn_Time", now):
            postUpdateIfChanged("pOther_Automatic_State_Solar", OFF)
        else:
            postUpdateIfChanged("pOther_Automatic_State_Solar", ON)
