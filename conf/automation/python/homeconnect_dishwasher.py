from openhab import rule, Registry, logger
from openhab.triggers import ItemStateChangeTrigger
from openhab.actions import Transformation

from shared.notification import NotificationHelper
from shared.user import UserHelper

import scope


@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_RemainingProgramTimeState"),
        ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_OperationState")
    ]
)
class Message:
    def execute(self, module, input):
        operation = Registry.getItemState("pGF_Kitchen_Dishwasher_OperationState")
        if operation != scope.NULL and operation != scope.UNDEF:
            mode = Transformation.transform("MAP", "homeconnect_operation.map", operation.toString() )
            msg = "{}".format(mode)

            runtime = Registry.getItemState("pGF_Kitchen_Dishwasher_RemainingProgramTimeState")

            #self.logger.info("{}".format(runtime))

            if runtime != scope.NULL and runtime != scope.UNDEF and runtime.intValue() > 0 and operation.toString() in ['Paused','Delayed','Run']:
                runtime = Transformation.transform("PY3", "homeconnect_runtime.py", "{}".format(runtime.intValue()) )
                msg = "{}, {}".format(msg,runtime)

            Registry.getItem("pGF_Kitchen_Dishwasher_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_OperationState", state="Finished")
    ]
)
class Notification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "Geschirrspüler", "Geschirr ist fertig", recipients = UserHelper.getPresentUser() )

@rule(triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_SaltEmptyState",state=scope.ON)
    ]
)
class SaltEmptyNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Geschirrspühler", "Salz nachfüllen" )

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_RinseEmptyState",state=scope.ON)
    ]
)
class RinseEmptyNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Geschirrspühler", "Klarspühler nachfüllen" )

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_MachineCareState",state=scope.ON)
    ]
)
class MachineCareNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Geschirrspühler", "Reiningungsprogramm nötig" )
