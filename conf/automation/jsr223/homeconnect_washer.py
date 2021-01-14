from shared.helper import rule, getItemState, postUpdateIfChanged, sendNotification, startTimer
from core.triggers import CronTrigger, ItemStateChangeTrigger
from core.actions import Transformation

@rule("homeconnect_washer.py")
class HomeConnectWasherMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_RemainingProgramTimeState"),
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_OperationState")
        ]

    def execute(self, module, input):
        mode = Transformation.transform("MAP", "washer_mode.map", getItemState("pGF_Utilityroom_Washer_OperationState").toString() )
        msg = u"{}".format(mode)
        
        runtime = getItemState("pGF_Utilityroom_Washer_RemainingProgramTimeState")
        
        #self.log.info(u"{}".format(runtime))
        
        if runtime != NULL and runtime != UNDEF and runtime.intValue() > 0:
            runtime = Transformation.transform("JS", "washer_runtime.js", u"{}".format(runtime.intValue()) )
            msg = u"{}, {}".format(msg,runtime)
            
        postUpdateIfChanged("pGF_Utilityroom_Washer_Message", msg)

@rule("homeconnect_washer.py")
class HomeConnectWasherNotificationRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_RemainingProgramTimeState"),
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_OperationState")
        ]

        self.checkTimer = None

    def notify(self,state):
        self.checkTimer = None
        sendNotification("Waschmaschine", u"Wäsche ist fertig" if state else u"Wäsche ist wahrscheinlich fertig" )
  
    def execute(self, module, input):
        if input['event'].getItemName() == "pGF_Utilityroom_Washer_RemainingProgramTimeState":
            runtime = input['event'].getItemState()
            if runtime != NULL and runtime != UNDEF and runtime.intValue() > 0 and self.checkTimer != None:
                # refresh timer with additional 10 min delay as a fallback
                self.checkTimer = startTimer(self.log, runtime.intValue() + 600, self.notify, args = [ False ], oldTimer = self.checkTimer)
        else:
            prevMode = input['event'].getOldItemState().toString()
            if prevMode != NULL and prevMode != UNDEF:
                currentMode = input['event'].getItemState().toString()
                if currentMode == "Run":
                    # start timer with initial 15 min delay as a fallback
                    self.checkTimer = startTimer(self.log, 900, self.notify, args = [ False ], oldTimer = self.checkTimer)
                elif currentMode == "Finished"and self.checkTimer != None:
                    self.checkTimer.cancel()
                    self.notify( True )
