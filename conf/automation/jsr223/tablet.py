import urllib2
from java.time import ZonedDateTime

from shared.helper import rule, getItemState, postUpdate, postUpdateIfChanged, itemLastChangeOlderThen, sendCommand, startTimer
from shared.triggers import ItemStateChangeTrigger, ItemCommandTrigger

from custom.presence import PresenceHelper


@rule("tablet.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOther_Presence_State") ]
        self.timer = None

    def execute(self, module, input):
        if getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING]:
            sendCommand("pOther_Scene7", OFF)
        else:
            sendCommand("pOther_Scene7", ON)
            

@rule("tablet.py")
class ManualReloadRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene7")]
        self.timer = None

    def process(self, i, cmd):
        if i > 5:
            self.log.error("Maximum number of attempts reached")
            postUpdate("pOther_Scene7", ON if cmd == OFF else OFF)
            return

        try:
            urllib2.urlopen("https://smartmarvin.de/wallmountedTabletLivingroom/?cmd=screen{}".format("Off" if cmd == OFF else "On")).read()
        except:
            self.log.info("Can't reach tablet. Retry in 1 seconds")
            self.timer = startTimer(self.log, 1,self.process, args=[i + 1, cmd])

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        self.timer = startTimer(self.log, 0,self.process, args=[0, input["event"].getItemCommand()])
