from java.time import ZonedDateTime
 
from shared.helper import rule, getItemState, getHistoricItemEntry, postUpdateIfChanged, startTimer, NotificationHelper
from shared.actions import Transformation
from shared.triggers import ItemStateChangeTrigger


@rule()
class HomeConnectWasherMessage:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_RemainingProgramTimeState"),
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_OperationState")
        ]

    def execute(self, module, input):
        prevState = input['event'].getOldItemState()
        if prevState == NULL or prevState == UNDEF:
            return

        # *** PROGRESS ***
        currentMode = input['event'].getItemState() if input['event'].getItemName() == "pGF_Utilityroom_Washer_OperationState" else getItemState("pGF_Utilityroom_Washer_OperationState")
        if currentMode == NULL or currentMode == UNDEF:
            return

        currentRuntime = input['event'].getItemState() if input['event'].getItemName() == "pGF_Utilityroom_Washer_RemainingProgramTimeState" else getItemState("pGF_Utilityroom_Washer_RemainingProgramTimeState")

        mode = Transformation.transform("MAP", "homeconnect_operation.map", currentMode.toString() )
        msg = u"{}".format(mode)

        if currentRuntime != NULL and currentRuntime != UNDEF and currentRuntime.intValue() > 0 and currentMode.toString() in ['Paused','Delayed','Run']:
            msg = u"{}, {}".format(msg, Transformation.transform("JS", "homeconnect_runtime.js", u"{}".format(currentRuntime.intValue()) ))

        postUpdateIfChanged("pGF_Utilityroom_Washer_Message", msg)

@rule()
class HomeConnectWasherNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_OperationState", state="Finished")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"Waschmaschine", u"Wäsche ist fertig" )

@rule()
class HomeConnectWasherDrumCleanNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_DrumCleanState",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Waschmachine", u"Trommelreinigung nötig" )
