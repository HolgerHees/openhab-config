from shared.helper import rule, getItemState, postUpdateIfChanged, NotificationHelper, UserHelper
from shared.triggers import ItemStateChangeTrigger


@rule()
class HomeConnectCoffeemakerMessage:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Power_State"),
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Program_Progress_State"),
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Operation_State")
        ]

    def execute(self, module, input):
      
        power_state = getItemState("pGF_Kitchen_Coffeemaker_Power_State")
        if power_state == ON:
            mode = getItemState("pGF_Kitchen_Coffeemaker_Operation_State").toString()
            msg = u"{}".format(mode)
            
            if mode != "Inactive":
                runtime = getItemState("pGF_Kitchen_Coffeemaker_Program_Progress_State")
                if runtime != NULL and runtime != UNDEF and runtime.intValue() > 0:
                    msg = u"{}, {} %".format(msg,runtime)
        else:
            msg = u"Aus"
            
        postUpdateIfChanged("pGF_Kitchen_Coffeemaker_Message", msg)

@rule()
class HomeConnectCoffeemakerDripTrayNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Drip_Tray_Full_State",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Kaffeemaschine", u"Auffangschale leeren", recipients = UserHelper.getPresentUser() )

@rule()
class HomeConnectCoffeemakerTankEmptyNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Tank_Empty_State",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Kaffeemaschine", u"Wasser nachfüllen", recipients = UserHelper.getPresentUser() )

@rule()
class HomeConnectCoffeemakerBeansEmptyNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Bean_Container_Empty_State",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Kaffeemaschine", u"Bohnen nachfüllen", recipients = UserHelper.getPresentUser() )
 
@rule()
class HomeConnectCoffeemakerCleaningNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Cleaning_Countdown",state=0)
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Kaffeemaschine", u"Reinigung nötig", recipients = UserHelper.getPresentUser() )

@rule()
class HomeConnectCoffeemakerCalcNotification:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Descaling_Countdown",state=0)
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Kaffeemaschine", u"Entkalkung nötig", recipients = UserHelper.getPresentUser() )
