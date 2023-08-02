from shared.triggers import CronTrigger
from shared.helper import rule, NotificationHelper

#from org.openhab.core.persistence.extensions import PersistenceExtensions
#from org.openhab.core.items import Item
#from org.slf4j import LoggerFactory

#log = LoggerFactory.getLogger("jsr223.jython")

#x = itemRegistry.getItem("pIndoor_Plant_Sensor_Main_Info")
#log.info(u"{}".format(x.getState()))
#log.info(u"{}".format(x.__class__))
#log.info(u"{}".format(isinstance(x, Item)))
##log.info(u"{}".format(dir(PersistenceExtensions.lastUpdate)))
##log.info(u"{}".format(PersistenceExtensions.lastUpdate.argslist))
#PersistenceExtensions.lastUpdate(x)
 

@rule("_test.py")
class TestRule:
    def __init__(self):
        #self.triggers = [
        #    CronTrigger("*/15 * * * * ?")
        #]
        #NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, u"Test", u"Info", recipients = ["hhees"] )

        pass

    def execute(self, module, input):     
        pass
  
  
            
             
                       
