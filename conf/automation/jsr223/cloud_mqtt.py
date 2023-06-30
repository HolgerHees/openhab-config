from shared.helper import rule, getGroupMemberChangeTrigger

@rule()
class CloudMqttPublish:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gPersistance_Mqtt")
     
    def execute(self, module, input):
        #self.log.info(u"{}".format(input['event'].getItemName(),input['event'].getItemState()))
        #mqttActions = actions.get("mqtt","mqtt:broker:mosquitto")
        #mqttActions.publishMQTT("mysensors-sub-1/1/4/1/0/2",u"{}".format(1 if getItemState("pOutdoor_WeatherStation_Rain_Heater") == ON else 0))
        
        mqttActions = actions.get("mqtt","mqtt:broker:cloud")
        mqttActions.publishMQTT("hhees/{}".format(input['event'].getItemName()),u"{}".format(input['event'].getItemState()))

 
