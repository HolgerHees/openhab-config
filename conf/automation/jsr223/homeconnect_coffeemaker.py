from shared.helper import rule, getItemState, postUpdateIfChanged, NotificationHelper
from custom.presence import PresenceHelper
from shared.triggers import CronTrigger, ItemStateChangeTrigger

@rule("homeconnect_coffeemaker.py")
class HomeConnectCoffeemakerMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
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

@rule("homeconnect_coffeemaker.py")
class HomeConnectCoffeemakerDripTrayNotificationRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Drip_Tray_Full_State",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Kaffeemaschine", u"Auffangschale leeren", recipients = PresenceHelper.getPresentRecipients() )

@rule("homeconnect_coffeemaker.py")
class HomeConnectCoffeemakerTankEmptyNotificationRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Tank_Empty_State",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Kaffeemaschine", u"Wasser nachfüllen", recipients = PresenceHelper.getPresentRecipients() )

@rule("homeconnect_coffeemaker.py")
class HomeConnectCoffeemakerBeansEmptyNotificationRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Bean_Container_Empty_State",state="ON")
        ]

    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, u"Kaffeemaschine", u"Bohnen nachfüllen", recipients = PresenceHelper.getPresentRecipients() )
 
