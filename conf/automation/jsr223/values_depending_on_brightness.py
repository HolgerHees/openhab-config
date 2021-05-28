from shared.helper import rule, getItemState, itemStateNewerThen, itemStateOlderThen, postUpdateIfChanged, postUpdate
from core.triggers import CronTrigger
from java.time import ZonedDateTime, Instant, ZoneId
 
@rule("values_depending_on_brightness.py")
class ValuesDependingOnBrightnessRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 * * * * ?")]

    def execute(self, module, input):
        now = ZonedDateTime.now()
        
        # pOutdoor_Astro_Dawn_Time
        # pOutdoor_Astro_Sunrise_Time
        # pOutdoor_Astro_Sunset_Time
        # pOutdoor_Astro_Dusk_Time
        
        cloudCover = getItemState("pOutdoor_Weather_Current_Cloud_Cover").intValue()
        
        if getItemState("pOther_Automatic_State_Rollershutter") == ON:
            
          
          
            _upTime = getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime().toInstant().toEpochMilli()
            _upTime = int(_upTime + ( cloudCover * 30.0 / 9.0 ) * 60 * 1000)

            _lastDownTime = getItemState("pOther_Automatic_State_Rollershutter_Down").getZonedDateTime().toInstant().toEpochMilli()

            if now.toInstant().toEpochMilli() > _upTime and _upTime > _lastDownTime:
                postUpdate("pOther_Automatic_State_Rollershutter", OFF)

            postUpdateIfChanged("pOther_Automatic_State_Rollershutter_Up", ZonedDateTime.ofInstant(Instant.ofEpochMilli(_upTime), ZoneId.systemDefault()).toLocalDateTime().toString() )
        else:
            _downTime = getItemState("pOutdoor_Astro_Dusk_Time").getZonedDateTime().toInstant().toEpochMilli()
            _downTime = int(_downTime - ( cloudCover * 30.0 / 9.0 ) * 60 * 1000)
            
            if now.toInstant().toEpochMilli() > _downTime:
                postUpdate("pOther_Automatic_State_Rollershutter", ON)
 
            postUpdateIfChanged("pOther_Automatic_State_Rollershutter_Down", ZonedDateTime.ofInstant(Instant.ofEpochMilli(_downTime), ZoneId.systemDefault()).toLocalDateTime().toString() )

        if itemStateOlderThen("pOutdoor_Astro_Sunset_Time", now) or itemStateNewerThen("pOutdoor_Astro_Sunrise_Time", now):
            postUpdateIfChanged("pOther_Automatic_State_Outdoorlights", ON)
        else:
            postUpdateIfChanged("pOther_Automatic_State_Outdoorlights", OFF)
            
        if itemStateOlderThen("pOutdoor_Astro_Dusk_Time", now) or itemStateNewerThen("pOutdoor_Astro_Dawn_Time", now):
            postUpdateIfChanged("pOther_Automatic_State_Solar", OFF)
        else:
            postUpdateIfChanged("pOther_Automatic_State_Solar", ON)
