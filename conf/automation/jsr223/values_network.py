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
            currentValue = input['event'].getItemState().intValue()
            prevValue = input['event'].getOldItemState().intValue()

            diffValue = ( currentValue - prevValue ) * 8
            diffTime = ( now - self.lastUpdate ) / 1000.0

            #self.log.info(u"{} {} {} {}".format(currentValue,prevValue,diffValue,diffTime))
            
            speed = round(diffValue / diffTime,1)
            
            postUpdateIfChanged("pGF_Corridor_Fritzbox_WanUpstreamCurrRate",speed)

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
            currentValue = input['event'].getItemState().intValue()
            prevValue = input['event'].getOldItemState().intValue()

            diffValue = ( currentValue - prevValue ) * 8
            diffTime = ( now - self.lastUpdate ) / 1000.0

            speed = round(diffValue / diffTime)
            
            postUpdateIfChanged("pGF_Corridor_Fritzbox_WanDownstreamCurrRate",speed)

            #self.log.info(u"Downstream {} MBit".format(speed))
        
        self.lastUpdate = now
