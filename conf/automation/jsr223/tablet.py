import time
import urllib2
from java.time import ZonedDateTime

from shared.helper import rule, getItemState, postUpdate, sendCommandIfChanged, startTimer
from shared.triggers import ItemStateChangeTrigger, ItemCommandTrigger

from custom.presence import PresenceHelper


@rule("tablet.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOther_Presence_State") ]
        self.timer = None

    def execute(self, module, input):
        if getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING]:
            sendCommandIfChanged("pOther_Scene7", OFF)
        else:
            sendCommandIfChanged("pOther_Scene7", ON)


@rule("tablet.py")
class TabletScreenRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene7")]
        self.timer = None

    def process(self, i, cmd):
        try:
            urllib2.urlopen("https://smartmarvin.de/wallmountedTabletLivingroom/?cmd=screen{}".format("Off" if cmd == OFF else "On")).read()
            time.sleep(1)
            status_result = urllib2.urlopen("https://smartmarvin.de/wallmountedTabletLivingroom/?cmd=getDeviceInfo").read()
            index = status_result.find("\"screenOn\": {}".format("false" if cmd == OFF else "true"))
            if index != -1:
                return

            msg = "Tablet screen action not successful"

        except Exception as e:
            msg = "Can't reach tablet"
            status_result = None

        if status_result is not None:
            self.log.info(status_result)

        if i > 5:
            self.log.error("Maximum number of attempts reached")
            postUpdate("pOther_Scene7", ON if cmd == OFF else OFF)
            return

        self.log.info("{}. Retry in 1 seconds".format(msg))
        self.timer = startTimer(self.log, 1,self.process, args=[i + 1, cmd])

    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

        self.timer = startTimer(self.log, 0,self.process, args=[0, input["event"].getItemCommand()])
