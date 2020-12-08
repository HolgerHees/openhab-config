from shared.helper import rule, sendNotification, sendCommand, getItem

from org.eclipse.smarthome.core.thing.link import ItemChannelLinkRegistry

from core import osgi

reg = osgi.get_service("org.eclipse.smarthome.core.thing.link.ItemChannelLinkRegistry")

@rule("_test.py")
class TestRule:
    def __init__(self):
        pass
        #for child in getItem("gGF_Lights").getAllMembers():
        #    self.log.info(u"{} {}".format(child.getName(),child.getState()))
                          
        #channels = reg.getBoundChannels("State_Holger_Presence").toArray()
        #self.log.info(u"{}".format(len(channels)))
        #for channeluuids in channels:
        #	self.log.info(str(channeluuids.getThingUID()))

    def execute(self, module, input):
        pass

#sendCommand("pGF_Utilityroom_Light_Ceiling_Brightness",REFRESH) 
 
