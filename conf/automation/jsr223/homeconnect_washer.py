from custom.helper import rule, getItemState, postUpdateIfChanged, sendNotification
from core.triggers import CronTrigger, ItemStateChangeTrigger
from core.actions import Transformation

@rule("homeconnect_washer.py")
class HomeConnectWasherMessageRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("Washer_RemainingProgramTimeState"),
            ItemStateChangeTrigger("Washer_OperationState")
        ]

    def execute(self, module, input):
        
        mode = Transformation.transform("MAP", "washer_mode.map", getItemState("Washer_OperationState").toString() )
        msg = u"{}".format(mode)
        
        runtime = getItemState("Washer_RemainingProgramTimeState")
        if runtime.intValue() > 0:
            runtime = Transformation.transform("JS", "washer_runtime.js", runtime.toString() )
            msg = u"{}, {}".format(msg,runtime)
            
        postUpdateIfChanged("Washer_Message", msg)


@rule("homeconnect_washer.py")
class HomeConnectWasherNotificationRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Washer_OperationState")
        ]

    def execute(self, module, input):
      
        currentMode = Transformation.transform("MAP", "washer_mode.map", input['event'].getItemState().toString() )
        prevMode = Transformation.transform("MAP", "washer_mode.map", input['event'].getOldItemState().toString() )
        
        if currentMode == "Fertig" and currentMode != prevMode:
            sendNotification("Waschmaschine", u"Wäsche ist fertig")
        
        #if mode == "Fertig":
