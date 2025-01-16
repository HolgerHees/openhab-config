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

        #self.check()

    def check(self):
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

    def execute(self, module, input):
        self.check()

@rule()
class HomeConnectDishwasherNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_OperationState", state="Finished")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"Geschirrspüler", u"Geschirr ist fertig", recipients = UserHelper.getPresentUser() )

@rule()
class HomeConnectDishwasherSaltEmptyNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_SaltEmptyState",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Geschirrspühler", u"Salz nachfüllen" )

@rule()
class HomeConnectDishwasherRinseEmptyNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_RinseEmptyState",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Geschirrspühler", u"Klarspühler nachfüllen" )

@rule()
class HomeConnectDishwasherMachineCareNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Dishwasher_MachineCareState",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Geschirrspühler", u"Reiningungsprogramm nötig" )
