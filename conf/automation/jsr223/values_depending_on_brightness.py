from java.time import ZonedDateTime, Instant, ZoneId

from shared.helper import rule, getItemState, itemStateNewerThen, itemStateOlderThen, postUpdateIfChanged, postUpdate
from shared.triggers import CronTrigger

from custom.sunprotection import SunProtectionHelper

 
@rule("values_depending_on_brightness.py")
class ValuesDependingOnBrightnessRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 * * * * ?")]
#        self.triggers = [CronTrigger("*/15 * * * * ?")]

    def execute(self, module, input):
        now = ZonedDateTime.now()
        
        # pOutdoor_Astro_Dawn_Time
        # pOutdoor_Astro_Sunrise_Time
        # pOutdoor_Astro_Sunset_Time
        # pOutdoor_Astro_Dusk_Time
        
        cloudCover = getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
        
        lightLevel = getItemState("pOutdoor_WeatherStation_Light_Level").intValue() if getItemState("pOutdoor_WeatherStation_Is_Working") == ON else 1000
        
        #self.log.info(str(cloudCover))
        
        nowInMillies = now.toInstant().toEpochMilli()
        
        automaticRollershutterState = getItemState("pOther_Automatic_State_Rollershutter").intValue()
        
        if automaticRollershutterState != SunProtectionHelper.STATE_ROLLERSHUTTER_UP:
            _upTime = getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime().toInstant().toEpochMilli()
            _upTime = int(_upTime + ( cloudCover * 30.0 / 9.0 ) * 60 * 1000)

            if now.getHour() < 12:               
                if nowInMillies >= _upTime:
                    postUpdate("pOther_Automatic_State_Rollershutter", SunProtectionHelper.STATE_ROLLERSHUTTER_UP)
                elif lightLevel > 0 and automaticRollershutterState != SunProtectionHelper.STATE_ROLLERSHUTTER_MAYBE_UP:
                    _upTime = getItemState("pOutdoor_Astro_Dawn_Time").getZonedDateTime().toInstant().toEpochMilli()
                    if nowInMillies > _upTime:
                        postUpdate("pOther_Automatic_State_Rollershutter", SunProtectionHelper.STATE_ROLLERSHUTTER_MAYBE_UP)

            postUpdateIfChanged("pOther_Automatic_State_Rollershutter_Up", ZonedDateTime.ofInstant(Instant.ofEpochMilli(_upTime), ZoneId.systemDefault()).toLocalDateTime().toString() )
        else:
            _downTime = getItemState("pOutdoor_Astro_Dusk_Time").getZonedDateTime().toInstant().toEpochMilli()
            _downTime = int(_downTime - ( cloudCover * 30.0 / 9.0 ) * 60 * 1000)
            
            if nowInMillies >= _downTime:
                postUpdate("pOther_Automatic_State_Rollershutter", SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN)
            elif lightLevel <= 0:
                _downTime = getItemState("pOutdoor_Astro_Sunset_Time").getZonedDateTime().toInstant().toEpochMilli()
                if nowInMillies >= _downTime:
                    postUpdate("pOther_Automatic_State_Rollershutter", SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN)
 
            postUpdateIfChanged("pOther_Automatic_State_Rollershutter_Down", ZonedDateTime.ofInstant(Instant.ofEpochMilli(_downTime), ZoneId.systemDefault()).toLocalDateTime().toString() )

        if lightLevel <= 0 or itemStateOlderThen("pOutdoor_Astro_Sunset_Time", now) or itemStateNewerThen("pOutdoor_Astro_Sunrise_Time", now):
            postUpdateIfChanged("pOther_Automatic_State_Outdoorlights", ON)
        else:
            postUpdateIfChanged("pOther_Automatic_State_Outdoorlights", OFF)
            
        if itemStateOlderThen("pOutdoor_Astro_Dusk_Time", now) or itemStateNewerThen("pOutdoor_Astro_Dawn_Time", now):
            postUpdateIfChanged("pOther_Automatic_State_Solar", OFF)
        else:
            postUpdateIfChanged("pOther_Automatic_State_Solar", ON)
