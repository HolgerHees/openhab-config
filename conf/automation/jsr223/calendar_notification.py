from java.time import ZonedDateTime

from shared.helper import rule, getItemState, sendCommand, itemStateNewerThen, itemStateOlderThen, NotificationHelper
from shared.triggers import CronTrigger

from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper


@rule()
class CalendarNotification:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 18 * * ?")]

        #sendCommand("pGF_Workroom_Alexa_CMD", u"Mache eine Ankündigung. Müllabholung, Papiertonnen")

        #AlexaHelper.sendTTS(u"Papiertonnen", header = u"Müllabholung")
        
    def append(self,active,state):
        if state == u"Laubsäcke":
            return
          
        active.append(state)

    def execute(self, module, input):
        notify_state = getItemState("pOther_Manual_State_Calendar_Event_Notify").intValue()
        # we don't want do be notified
        if notify_state == 0:
            return
      
        #day = getItemState("pGF_Corridor_Garbage_Appointments_Begin_0")
        #info = getItemState("pGF_Corridor_Garbage_Appointments_Info_0")
        #self.log.info(u"{} {}".format(day,info))
        
        active = []

        if itemStateNewerThen("pGF_Corridor_Garbage_Appointments_Begin_0",ZonedDateTime.now()) and itemStateOlderThen("pGF_Corridor_Garbage_Appointments_Begin_0",ZonedDateTime.now().plusHours(12)):
            self.append(active,getItemState("pGF_Corridor_Garbage_Appointments_Info_0").toString().strip())
        
        if itemStateNewerThen("pGF_Corridor_Garbage_Appointments_Begin_1",ZonedDateTime.now()) and itemStateOlderThen("pGF_Corridor_Garbage_Appointments_Begin_1",ZonedDateTime.now().plusHours(12)):
            self.append(active,getItemState("pGF_Corridor_Garbage_Appointments_Info_1").toString().strip())

        if itemStateNewerThen("pGF_Corridor_Garbage_Appointments_Begin_2",ZonedDateTime.now()) and itemStateOlderThen("pGF_Corridor_Garbage_Appointments_Begin_2",ZonedDateTime.now().plusHours(12)):
            self.append(active,getItemState("pGF_Corridor_Garbage_Appointments_Info_2").toString().strip())

        if len(active) > 0:
            push_msg = ", ".join(active)
            alexa_msg = " und ".join(active)

            if notify_state & 1:
                NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"Müllabholung",push_msg)

            if notify_state & 2 and getItemState("pOther_Presence_State").intValue() == PresenceHelper.STATE_PRESENT:
                AlexaHelper.sendTTS(alexa_msg, header = u"Müllabholung")


