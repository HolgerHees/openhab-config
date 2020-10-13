from custom.helper import rule, getItemState, postUpdateIfChanged, sendNotification
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
            ItemStateChangeTrigger("Washer_OperationState")
        ]

    def execute(self, module, input):
      
        currentMode = input['event'].getItemState().toString()
        prevMode = input['event'].getOldItemState().toString()
        
        if currentMode == "Finished" and prevMode == "Run":
            sendNotification("Waschmaschine", u"Wäsche ist fertig")
        
        #if mode == "Fertig":
