from shared.helper import rule, getItemState, itemStateNewerThen, itemStateOlderThen, sendNotification
from core.triggers import CronTrigger

from java.time import ZonedDateTime


@rule("calendar_notification.py")
class CalendarNotificationRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 18 * * ?")]
        
    def append(self,active,state):
        if state == u"Laubsäcke":
            return
          
        active.append(state)

    def execute(self, module, input):
      
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
            msg = ", ".join(active)
            sendNotification(u"Müllabholung",msg)
            #self.log.info(u"{}".format(msg))
