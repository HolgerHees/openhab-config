from shared.helper import rule, postUpdateIfChanged, getStableMinMaxItemState
from shared.actions import HTTP
from shared.triggers import ItemStateChangeTrigger


@rule("values_network_trigger.py")
class ValuesNetworkSpeedRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Corridor_Speedtest_Rerun", state="ON"),
            ItemStateChangeTrigger("pGF_Corridor_Speedtest_Location"),
            ItemStateChangeTrigger("pGF_Corridor_Speedtest_DownstreamRate")
        ]
        
    def execute(self, module, input):
        if input['event'].getItemName() == "pGF_Corridor_Speedtest_Rerun":
            HTTP.sendHttpGetRequest("http://localhost:8507/triggerSpeedtest")
        elif input['event'].getItemName() == "pGF_Corridor_Speedtest_Location":
            if input['event'].getItemState().toString() != "Aktiv":
                postUpdateIfChanged("pGF_Corridor_Speedtest_Rerun",OFF)
        else:
            downstream = input['event'].getItemState().doubleValue()
            #if downstream < 750:
            if downstream < 400:
                _, _, maxDownstream = getStableMinMaxItemState(now, "pGF_Corridor_Speedtest_DownstreamRate", 60 * 4)
                #if maxDownstream < 750:
                if maxDownstream < 400:
                    self.log.error(u"Speedtest detect slow wan connection: {} MBit".format(int(downstream)))
