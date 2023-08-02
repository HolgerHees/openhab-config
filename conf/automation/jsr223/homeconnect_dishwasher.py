from shared.helper import rule, getItemState, postUpdateIfChanged, startTimer, NotificationHelper, UserHelper
from shared.actions import Transformation
from shared.triggers import ItemStateChangeTrigger

 
@rule()
class HomeConnectDishwasherMessage:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_RemainingProgramTimeState"),
            ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_OperationState")
        ]

    def execute(self, module, input):
        operation = getItemState("pGF_Kitchen_Dishwasher_OperationState")
        if operation != NULL and operation != UNDEF:
            mode = Transformation.transform("MAP", "homeconnect_operation.map", operation.toString() )
            msg = u"{}".format(mode)
            
            runtime = getItemState("pGF_Kitchen_Dishwasher_RemainingProgramTimeState")
            
            #self.log.info(u"{}".format(runtime))
            
            if runtime != NULL and runtime != UNDEF and runtime.intValue() > 0 and operation.toString() in ['Paused','Delayed','Run']:
                runtime = Transformation.transform("JS", "homeconnect_runtime.js", u"{}".format(runtime.intValue()) )
                msg = u"{}, {}".format(msg,runtime)
                
            postUpdateIfChanged("pGF_Kitchen_Dishwasher_Message", msg)

@rule()
class HomeConnectDishwasherNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_RemainingProgramTimeState"),
            ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_OperationState")
        ]

        self.checkTimer = None

    def notify(self,state):
        self.checkTimer = None
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"Geschirrspüler", u"Geschirr ist fertig" if state else u"Geschirr ist wahrscheinlich fertig", recipients = UserHelper.getPresentUser() )
  
    def execute(self, module, input):
        if input['event'].getItemName() == "pGF_Kitchen_Dishwasher_RemainingProgramTimeState":
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
