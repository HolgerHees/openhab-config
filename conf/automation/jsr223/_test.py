from shared.helper import rule, sendNotification, sendCommand, getItem

from org.eclipse.smarthome.core.thing.link import ItemChannelLinkRegistry

@rule("_test.py")
class TestRule:
    def __init__(self):
        pass

    def execute(self, module, input):
        pass

#sendCommand("pGF_Utilityroom_Light_Ceiling_Powered",REFRESH) 
 
