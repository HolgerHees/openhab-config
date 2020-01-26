from custom.helper import rule, getNow, itemStateNewerThen, itemStateOlderThen, postUpdateIfChanged
from core.triggers import CronTrigger

@rule("values_depending_on_brightness.py")
class ValuesDependingOnBrightnessRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 * * * * ?")]

    def execute(self, module, input):
        now = getNow()

        isBeforeSunrise = itemStateNewerThen("Sunrise_Time", now)

        if itemStateOlderThen("Sunset_Time", now) or isBeforeSunrise:
            postUpdateIfChanged("State_Outdoorlights", ON)
        else:
            postUpdateIfChanged("State_Outdoorlights", OFF)
            
        isAfterDusk = itemStateOlderThen("Dusk_Time", now)

        if isAfterDusk or isBeforeSunrise:
            postUpdateIfChanged("State_Rollershutter", ON)
        else:
            postUpdateIfChanged("State_Rollershutter", OFF)

        if isAfterDusk or itemStateNewerThen("Dawn_Time", now):
            postUpdateIfChanged("State_Solar", OFF)
        else:
            postUpdateIfChanged("State_Solar", ON)
