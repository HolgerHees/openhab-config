from shared.helper import rule, getNow, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger

@rule("values_network.py")
class ValuesNetworkOutgoingTrafficRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Corridor_Fritzbox_WanTotalBytesSent")
        ]
        self.lastUpdate = -1
        
    def execute(self, module, input):
        #self.log.info(u"{}".format(input))

        now = getNow().getMillis()

        if self.lastUpdate != -1:
            currentValue = input['event'].getItemState().longValue()
            prevValue = input['event'].getOldItemState().longValue()

            diffValue = ( currentValue - prevValue ) * 8
            diffTime = ( now - self.lastUpdate ) / 1000.0

            #self.log.info(u"{} {} {} {}".format(currentValue,prevValue,diffValue,diffTime))
            
            speed = round(diffValue / diffTime)
            postUpdateIfChanged("pGF_Corridor_Fritzbox_WanUpstreamCurrRate",speed)
            #else:
            #self.log.info(u"Outgoing - currentValue: {}".format(currentValue))
            #self.log.info(u"Outgoing - prevValue: {}".format(prevValue))
            #self.log.info(u"Outgoing - diffValue: {}".format(diffValue))
            #self.log.info(u"Outgoing - now: {}".format(now))
            #self.log.info(u"Outgoing - lastUpdate: {}".format(self.lastUpdate))
            #self.log.info(u"Outgoing - diffTime: {}".format(diffTime))
            #self.log.info(u"Outgoing - speed: {}".format(speed))

            #self.log.info(u"Upstream {} MBit".format(speed))
        
        self.lastUpdate = now
      
@rule("values_network.py")
class ValuesNetworkIncommingTrafficRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Corridor_Fritzbox_WanTotalBytesReceived")
        ]
        self.lastUpdate = -1

    def execute(self, module, input):
        #self.log.info(u"{}".format(input))

        now = getNow().getMillis()

        if self.lastUpdate != -1:
            currentValue = input['event'].getItemState().longValue()
            prevValue = input['event'].getOldItemState().longValue()

            diffValue = ( currentValue - prevValue ) * 8
            diffTime = ( now - self.lastUpdate ) / 1000.0

            speed = round(diffValue / diffTime)
            postUpdateIfChanged("pGF_Corridor_Fritzbox_WanDownstreamCurrRate",speed)
            #else:
            #self.log.info(u"Incomming - currentValue: {}".format(currentValue))
            #self.log.info(u"Incomming - prevValue: {}".format(prevValue))
            #self.log.info(u"Incomming - diffValue: {}".format(diffValue))
            #self.log.info(u"Incomming - now: {}".format(now))
            #self.log.info(u"Incomming - lastUpdate: {}".format(self.lastUpdate))
            #self.log.info(u"Incomming - diffTime: {}".format(diffTime))
            #self.log.info(u"Incomming - speed: {}".format(speed))

            #self.log.info(u"Downstream {} MBit".format(speed))
        
        self.lastUpdate = now
