from shared.triggers import CronTrigger
from shared.helper import rule, sendCommand, getItem, NotificationHelper

@rule("_test.py")
class TestRule:
    def __init__(self):
        #self.triggers = [
        #    CronTrigger("*/15 * * * * ?")
        #]
        #NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, u"Test", u"Info", recipients = ["hhees"] )
        pass

    def execute(self, module, input):     
#        test = 1 / 0
        pass

#sendCommand("pGF_Utilityroom_Light_Ceiling_Powered",REFRESH) 
  
  
            
             
                       
