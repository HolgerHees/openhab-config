import urllib2

from custom.helper import rule, getItemState, postUpdate, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger, ItemCommandTrigger

@rule("tablet.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("State_Presence")
        ]

    def execute(self, module, input):
        if input["event"].getItemState().intValue() != 1:
            urllib2.urlopen("http://192.168.0.40:5000/sleep").read()
        else:
            urllib2.urlopen("http://192.168.0.40:5000/wakeup").read()


@rule("tablet.py")
class ManualReloadRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Scene7")]

    def execute(self, module, input):
        urllib2.urlopen("http://192.168.0.40:5000/reload").read()
        postUpdate("Scene7", OFF)


@rule("tablet.py")
class ManualWakeupRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Scene8")]

    def execute(self, module, input):
        if input["event"].getItemCommand() == OFF:
            urllib2.urlopen("http://192.168.0.40:5000/sleep").read()
        else:
            urllib2.urlopen("http://192.168.0.40:5000/wakeup").read()


@rule("tablet.py")
class ManualThemeRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Scene9")]

    def execute(self, module, input):
        if input["event"].getItemCommand() == OFF:
            urllib2.urlopen("http://192.168.0.40:5000/disableLightTheme").read()
        else:
            urllib2.urlopen("http://192.168.0.40:5000/enableLightTheme").read()
