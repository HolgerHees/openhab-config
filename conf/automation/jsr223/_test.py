from shared.triggers import CronTrigger
from shared.helper import rule, NotificationHelper, getItem

from org.openhab.core.library.items import NumberItem

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
from shared.semantic.command_processor import CommandProcessor
from custom.alexa import AlexaHelper


@rule("_test.py")
class TestRule:
    def __init__(self):
        #self.triggers = [
        #    CronTrigger("*/15 * * * * ?")
        #]
        #NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, u"Test", u"Info", recipients = ["hhees"] )

        processor = CommandProcessor(self.log,ir)

        #item = getItem("pGF_Boxroom_Air_Sensor_CO2_Value")
        #if isinstance(item, NumberItem):
        #    unit = item.getUnit()
        #    self.log.info(u"{}".format(unit))
        #    self.log.info(u"{}".format(unit))

        voice_command, client_id = processor.parseData(u"Wie warm ist es im Wohnzimmer")
        self.log.info(u"{}".format(voice_command))

        fallback_location_name = AlexaHelper.getLocationByDeviceId(client_id)

        actions = processor.process(voice_command, fallback_location_name)
        msg, is_valid = processor.applyActions(actions,voice_command,True)

        self.log.info(u"{}".format(msg))


        pass

    def execute(self, module, input):     
        pass
  
  
            
             
                       
