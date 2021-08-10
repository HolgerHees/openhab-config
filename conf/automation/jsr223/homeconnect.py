from shared.helper import rule, postUpdateIfChanged, getItemState, getThing
from shared.triggers import CronTrigger, ThingStatusChangeTrigger

#https://github.com/bruestel/org.openhab.binding.homeconnect/tree/2.5.x-next/bundles/org.openhab.binding.homeconnect#notification-on-credential-error
@rule("homeconnect.py")
class HomeConnectStateRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ThingStatusChangeTrigger("homeconnect:api_bridge:default")
        ]
        self.check()
        
    def check(self):
        thing = getThing("homeconnect:api_bridge:default")
        status = thing.getStatus()
        info = thing.getStatusInfo()
        
        if status is not None and info is not None:
            #self.log.info(u"Home Connect bridge status: '{}',  detail: '{}'".format(status.toString(),info.toString()))
            if status.toString() == 'OFFLINE':
                postUpdateIfChanged("pOther_State_Message_Homeconnect",info.toString())
            else:
                postUpdateIfChanged("pOther_State_Message_Homeconnect","Alles ok")

    def execute(self, module, input):
        self.check()
