from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger

from shared.notification import NotificationHelper

from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper
from custom.flags import FlagHelper

from datetime import datetime, timedelta


@rule(
    triggers = [
        GenericCronTrigger("0 0 18 * * ?")
    ]
)
class Notification:
    def append(self,active,state):
        if state == "Laubsäcke":
            return
        active.append(state)

    def execute(self, module, input):
        flags = Registry.getItemState("pOther_Manual_State_Calendar_Event_Notify").intValue()
        # we don't want do be notified
        if FlagHelper.hasFlag(FlagHelper.OFF, flags):
            return

        #day = Registry.getItemState("pGF_Corridor_Garbage_Appointments_Begin_0")
        #info = Registry.getItemState("pGF_Corridor_Garbage_Appointments_Info_0")
        #self.logger.info("{} {}".format(day,info))

        active = []
        now = datetime.now().astimezone()

        begin = Registry.getItemState("pGF_Corridor_Garbage_Appointments_Begin_0")
        if begin > now and begin < ( now + timedelta(hours=12) ):
            self.append(active,Registry.getItemState("pGF_Corridor_Garbage_Appointments_Info_0").toString().strip())

        begin = Registry.getItemState("pGF_Corridor_Garbage_Appointments_Begin_1")
        if begin > now and begin < ( now + timedelta(hours=12) ):
            self.append(active,Registry.getItemState("pGF_Corridor_Garbage_Appointments_Info_1").toString().strip())

        begin = Registry.getItemState("pGF_Corridor_Garbage_Appointments_Begin_2")
        if begin > now and begin < ( now + timedelta(hours=12) ):
            self.append(active,Registry.getItemState("pGF_Corridor_Garbage_Appointments_Info_2").toString().strip())

        if len(active) > 0:
            push_msg = ", ".join(active)
            alexa_msg = " und ".join(active)

            if FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags):
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "Müllabholung",push_msg)

            if FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags) and getItemState("pOther_Presence_State").intValue() == PresenceHelper.STATE_PRESENT:
                AlexaHelper.sendTTS(alexa_msg, header = "Müllabholung")
