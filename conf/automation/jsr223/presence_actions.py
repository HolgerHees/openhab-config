import urllib2

from marvin.helper import rule, getItemState, postUpdate, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger


@rule("presence_actions.py")
class LeavingRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Presence","0")]

    def execute(self, module, input):
        #self.log.info("test")
        postUpdateIfChanged("State_Notify", ON)


@rule("presence_actions.py")
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
