from shared.helper import rule, postUpdateIfChanged, getThing, startTimer
from shared.triggers import ThingStatusChangeTrigger


#https://github.com/bruestel/org.openhab.binding.homeconnect/tree/2.5.x-next/bundles/org.openhab.binding.homeconnect#notification-on-credential-error
#@rule()
#class HomeConnectState:
#    def __init__(self):
#        self.triggers = [
#            ThingStatusChangeTrigger("homeconnect:api_bridge:default")
#        ]

#        startTimer(self.log, 5, self.check)

#    def check(self):
#        thing = getThing("homeconnect:api_bridge:default")
#        status = thing.getStatus()

#        #self.log.info(u"Home Connect bridge status: '{}',  detail: '{}'".format(status.toString(),info.toString()))
#        if status.toString() != "ONLINE":
#            info = thing.getStatusInfo()
#            postUpdateIfChanged("eOther_Error_Homeconnect_Message", "Thing: {}".format(info.toString()))
#        else:
#            postUpdateIfChanged("eOther_Error_Homeconnect_Message","")

#    def execute(self, module, input):
#        self.check()
