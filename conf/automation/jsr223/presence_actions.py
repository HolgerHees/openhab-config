import urllib2

from marvin.helper import rule, getItemState, postUpdate, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger


@rule("presence_actions.py")
class LeavingRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Presence",state="0")]

    def execute(self, module, input):
        #self.log.info("test")
        postUpdateIfChanged("State_Notify", ON)

