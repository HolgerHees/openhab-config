import time
import urllib2

from shared.helper import rule, getItemState, postUpdate, sendCommandIfChanged, startTimer
from shared.triggers import ItemStateChangeTrigger, ItemCommandTrigger
from custom.presence import PresenceHelper

from custom_configuration import livingroom_api


@rule()
class TabletScreen:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State")]
        self.in_progress = False

        #status_result = urllib2.urlopen(livingroom_api + "&cmd=getDeviceInfo").read()
        #self.log.info(status_result)

    def switch(self,i, cmd):
        try:
            action = "Off" if cmd == OFF else "On"
            self.log.info("Try tablet switch {}".format(action))

            urllib2.urlopen(livingroom_api + "&cmd=screen{}".format(action)).read()

            time.sleep(1)

            status_result = urllib2.urlopen(livingroom_api + "&cmd=getDeviceInfo").read()
            index = status_result.find("\"screenOn\": {}".format("false" if cmd == OFF else "true"))
            if index != -1:
                self.log.info("Tablet switch successful")
                return True

            self.log.error("Tablet switch not successful")
            self.log.info(status_result)
        except Exception as e:
            if i > 5 or !isinstance(e, urllib2.URLError):
                self.log.error("{}: {}".format(e.__class__, str(e)))
                self.log.error("Can't reach tablet")

        return False

    def process(self, i, requested_cmd):
        is_success = self.switch(i, requested_cmd)

        active__cmd = requested_cmd if i == 0 else self.getRequestedCommand( getItemState("pOther_Presence_State").intValue() )

        if requested_cmd == active__cmd:
            if not is_success:
                if i > 5:
                    self.log.error("Maximum number of attempts reached")
                else:
                    self.log.warn("Retry in 1 seconds")
                    time.sleep(1)
                    self.process(i + 1, requested_cmd)

            self.in_progress = False
            return

        self.log.info("Requested tablet state changed")
        self.process(0, active__cmd)

    def getRequestedCommand(self, state):
        return getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING]

    def execute(self, module, input):
        if self.in_progress:
            return

        self.in_progress = True
        startTimer(self.log, 0,self.process, args=[0, self.getRequestedCommand( input["event"].getItemState().intValue() )])
