import urllib2
from java.time import ZonedDateTime

from shared.helper import rule, getItemState, postUpdate, postUpdateIfChanged, itemLastChangeOlderThen, sendCommand
from core.triggers import ItemStateChangeTrigger, ItemCommandTrigger

@rule("tablet.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State"),
            ItemStateChangeTrigger("gGF_Lights")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "pOther_Presence_State":
            if input["event"].getItemState().intValue() != 1:
                urllib2.urlopen("http://192.168.0.40:5000/sleep").read()
            else:
                urllib2.urlopen("http://192.168.0.40:5000/wakeup").read()
        # check for itemLastChangeOlderThen to avoid flapping, because gGF_Lights is affected by pOther_Presence_State
        elif getItemState('pOther_Presence_State').intValue() == 2 and itemLastChangeOlderThen("pOther_Presence_State",ZonedDateTime.now().minusSeconds(5)):
            if input["event"].getItemState() == OFF:
                urllib2.urlopen("http://192.168.0.40:5000/sleep").read()
            else:
                urllib2.urlopen("http://192.168.0.40:5000/wakeup").read()


@rule("tablet.py")
class ManualReloadRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene7")]

    def execute(self, module, input):
        #sendCommand("pOther_Helper_HabpanelViewer_Control_Cmd", "RELOAD")
        urllib2.urlopen("http://192.168.0.40:5000/reload").read()
        postUpdate("pOther_Scene7", OFF)


@rule("tablet.py")
class ManualWakeupRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene8")]

    def execute(self, module, input):
        if input["event"].getItemCommand() == OFF:
            urllib2.urlopen("http://192.168.0.40:5000/sleep").read()
        else:
            urllib2.urlopen("http://192.168.0.40:5000/wakeup").read()


@rule("tablet.py")
class ManualThemeRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene9")]

    def execute(self, module, input):
        if input["event"].getItemCommand() == OFF:
            urllib2.urlopen("http://192.168.0.40:5000/disableLightTheme").read()
        else:
            urllib2.urlopen("http://192.168.0.40:5000/enableLightTheme").read()
