from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from shared.notification import NotificationHelper
from shared.user import UserHelper


@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Power_State"),
        ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Program_Progress_State"),
        ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Operation_State")
    ]
)
class Message:
    def execute(self, module, input):
        power_state = Registry.getItemState("pGF_Kitchen_Coffeemaker_Power_State")
        if power_state == ON:
            mode = Registry.getItemState("pGF_Kitchen_Coffeemaker_Operation_State").toString()
            msg = "{}".format(mode)
            
            if mode != "Inactive":
                runtime = Registry.getItemState("pGF_Kitchen_Coffeemaker_Program_Progress_State")
                if runtime != NULL and runtime != UNDEF and runtime.intValue() > 0:
                    msg = "{}, {} %".format(msg,runtime)
        else:
            msg = "Aus"
            
        Registry.getItem("pGF_Kitchen_Coffeemaker_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Drip_Tray_Full_State",state="ON")
    ]
)
class DripTrayNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Kaffeemaschine", "Auffangschale leeren", recipients = UserHelper.getPresentUser() )

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Tank_Empty_State",state="ON")
    ]
)
class TankEmptyNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Kaffeemaschine", "Wasser nachfüllen", recipients = UserHelper.getPresentUser() )

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Bean_Container_Empty_State",state="ON")
    ]
)
class BeansEmptyNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Kaffeemaschine", "Bohnen nachfüllen", recipients = UserHelper.getPresentUser() )
 
@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Cleaning_Countdown",state=0)
    ]
)
class CleaningNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Kaffeemaschine", "Reinigung nötig", recipients = UserHelper.getPresentUser() )

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Kitchen_Coffeemaker_Descaling_Countdown",state=0)
    ]
)
class CalcNotification:
    def execute(self, module, input):
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_INFO, "Kaffeemaschine", "Entkalkung nötig", recipients = UserHelper.getPresentUser() )
