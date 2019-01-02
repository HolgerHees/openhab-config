import urllib2

from marvin.helper import rule, getItemState, postUpdate
from core.triggers import ItemStateChangeTrigger


@rule("presence_actions.py")
class AutoWakeupRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("State_Presence")
        ]

    def execute(self, module, input):
        if input["event"].getItemState() != 1:
            urllib2.urlopen("http://192.168.0.40:5000/sleep").read()
        else:
            urllib2.urlopen("http://192.168.0.40:5000/wakeup").read()


@rule("presence_actions.py")
class ReloadRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Scene7")]

    def execute(self, module, input):
        urllib2.urlopen("http://192.168.0.40:5000/reload").read()
        postUpdate("Scene7", OFF)


@rule("presence_actions.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Scene8")]

    def execute(self, module, input):
        if getItemState("Scene8") == OFF:
            urllib2.urlopen("http://192.168.0.40:5000/sleep").read()
        else:
            urllib2.urlopen("http://192.168.0.40:5000/wakeup").read()


@rule("presence_actions.py")
class ThemeRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Scene9")]

    def execute(self, module, input):
        if getItemState("Scene9") == OFF:
            urllib2.urlopen("http://192.168.0.40:5000/disableLightTheme").read()
        else:
            urllib2.urlopen("http://192.168.0.40:5000/enableLightTheme").read()
