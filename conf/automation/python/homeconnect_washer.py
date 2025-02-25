from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger
from openhab.actions import Transformation

from shared.notification import NotificationHelper


@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Washer_RemainingProgramTimeState"),
        ItemStateChangeTrigger("pGF_Utilityroom_Washer_OperationState")
    ]
)
class Message:
    def execute(self, module, input):
        previous_state = input['event'].getOldItemState()
        if previous_state == NULL or previous_state == UNDEF:
            return

        # *** PROGRESS ***
        current_mode = input['event'].getItemState() if input['event'].getItemName() == "pGF_Utilityroom_Washer_OperationState" else Registry.getItemState("pGF_Utilityroom_Washer_OperationState")
        if current_mode == NULL or current_mode == UNDEF:
            return

        current_runtime = input['event'].getItemState() if input['event'].getItemName() == "pGF_Utilityroom_Washer_RemainingProgramTimeState" else Registry.getItemState("pGF_Utilityroom_Washer_RemainingProgramTimeState")

        mode = Transformation.transform("MAP", "homeconnect_operation.map", current_mode.toString() )
        msg = "{}".format(mode)

        if current_runtime != NULL and current_runtime != UNDEF and current_runtime.intValue() > 0 and current_mode.toString() in ['Paused','Delayed','Run']:
            msg = "{}, {}".format(msg, Transformation.transform("JS", "homeconnect_runtime.js", "{}".format(current_runtime.intValue()) ))

        Registry.getItem("pGF_Utilityroom_Washer_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Washer_OperationState", state="Finished")
    ]
)
class Notification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "Waschmaschine", "Wäsche ist fertig" )

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Washer_DrumCleanState",state="ON")
    ]
)
class DrumCleanNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Waschmachine", "Trommelreinigung nötig" )
