from shared.helper import rule, sendNotification, sendCommand

from org.eclipse.smarthome.core.thing.link import ItemChannelLinkRegistry

from core import osgi

reg = osgi.get_service("org.eclipse.smarthome.core.thing.link.ItemChannelLinkRegistry")

@rule("_test.py")
class TestRule:
    def __init__(self):
        channels = reg.getBoundChannels("State_Holger_Presence").toArray()
        self.log.info(u"{}".format(len(channels)))
        for channeluuids in channels:
			self.log.info(str(channeluuids.getThingUID()))
      
        pass

    def execute(self, module, input):
        pass

#sendCommand("Light_FF_Utilityroom_Ceiling",REFRESH) 
