from shared.helper import rule, getItemState, postUpdateIfChanged, sendNotification, startTimer
from core.triggers import CronTrigger, ItemStateChangeTrigger
from core.actions import Transformation

@rule("homeconnect_washer.py")
class HomeConnectWasherMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("Washer_RemainingProgramTimeState"),
            ItemStateChangeTrigger("Washer_OperationState")
        ]

    def execute(self, module, input):
        
        mode = Transformation.transform("MAP", "washer_mode.map", getItemState("Washer_OperationState").toString() )
        msg = u"{}".format(mode)
        
        runtime = getItemState("Washer_RemainingProgramTimeState")
        
        #self.log.info(u"{}".format(runtime))
        
        if runtime != NULL and runtime.intValue() > 0:
            runtime = Transformation.transform("JS", "washer_runtime.js", u"{}".format(runtime.intValue()) )
            msg = u"{}, {}".format(msg,runtime)
            
        postUpdateIfChanged("Washer_Message", msg)

@rule("homeconnect_washer.py")
class HomeConnectWasherNotificationRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Washer_RemainingProgramTimeState"),
            ItemStateChangeTrigger("Washer_OperationState")
        ]

        self.checkTimer = None

    def notify(self,state):
        self.checkTimer = None
        sendNotification("Waschmaschine", u"Wäsche ist fertig")
  
    def execute(self, module, input):
        if input['event'].getItemName() == "Washer_RemainingProgramTimeState":
            runtime = input['event'].getItemState()
            if runtime != NULL and runtime != UNDEF and runtime.intValue() > 0:
                self.checkTimer = startTimer(self.log, runtime.intValue(), self.notify, args = [ False ], oldTimer = self.checkTimer)
        else:
            if currentMode == "Finished" and self.checkTimer != None:
                self.checkTimer.cancel()
                self.notify( True )
                
            #prevMode = input['event'].getOldItemState().toString()
            #if prevMode == "Run":
              
        #if prevMode == "Run" or self.checkTimer != None:
        #    if self.checkTimer:
        #        self.checkTimer.cancel()

        #    currentMode = input['event'].getItemState().toString()
        #    if currentMode == "Finished":
        #        self.notify( True )
        #    elif currentMode == "NULL":
        #        runtime = getItemState("Washer_RemainingProgramTimeState")

        #if currentMode == "Run":
        #    self.isRunning = True
        #elif currentMode == "Finished" and self.isRunning == True:
        #    sendNotification("Waschmaschine", u"Wäsche ist fertig")
        #    self.isRunning = False
        
        #if mode == "Fertig":
