import urllib2
from java.time import ZonedDateTime

from shared.helper import rule, getItemState, postUpdate, postUpdateIfChanged, itemLastChangeOlderThen, sendCommand
from shared.triggers import ItemStateChangeTrigger, ItemCommandTrigger

from custom.presence import PresenceHelper


@rule("tablet.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State",state=PresenceHelper.STATE_AWAY),
            ItemStateChangeTrigger("pOther_Presence_State",state=PresenceHelper.STATE_SLEEPING),
            ItemStateChangeTrigger("pGF_Livingroom_Motiondetector_State",state="OPEN")
        ]
        self.isSleeping = False
        self.timer = None
        
    def sleep(self):
        if !self.isSleeping:
            urllib2.urlopen("http://192.168.0.40:5000/sleep").read()
            self.isSleeping = True
            
    def delayedSleep(self):
        if getItemState("pOther_Presence_State").intValue() != PresenceHelper.STATE_PRESENT:
            self.sleep()
            
    def wakeup(self):
        if self.isSleeping:
            urllib2.urlopen("http://192.168.0.40:5000/wakeup").read()
            self.isSleeping = False
                
    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
            
        if input['event'].getItemName() == "pOther_Presence_State":
            self.sleep()
        else:
            self.wakeup()
            
            if getItemState("pOther_Presence_State").intValue() != PresenceHelper.STATE_PRESENT:
                self.timer = createTimer(self.log, 600,self.delayedSleep) # 10 min
                self.timer.start()
            

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
