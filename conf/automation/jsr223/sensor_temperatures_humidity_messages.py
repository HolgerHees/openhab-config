from shared.helper import rule, getItemState, postUpdateIfChanged, startTimer
from shared.triggers import ItemStateChangeTrigger


infoConfig = [
    ["pGF_Livingroom_Air_Sensor_Message", "pGF_Livingroom_Air_Sensor_Temperature_Value", "pGF_Livingroom_Air_Sensor_Humidity_Value", None, "pGF_Livingroom_Temperature_Desired"],
    ["pGF_Boxroom_Air_Sensor_Message", "pGF_Boxroom_Air_Sensor_Temperature_Value", "pGF_Boxroom_Air_Sensor_Humidity_Value", "pGF_Boxroom_Air_Sensor_CO2_Value", None],
    ["pGF_Workroom_Air_Sensor_Message", "pGF_Workroom_Air_Sensor_Temperature_Value", "pGF_Workroom_Air_Sensor_Humidity_Value", None, "pGF_Workroom_Temperature_Desired"],
    ["pGF_Guesttoilet_Air_Sensor_Message", "pGF_Guesttoilet_Air_Sensor_Temperature_Value", "pGF_Guesttoilet_Air_Sensor_Humidity_Value", None, "pGF_Guesttoilet_Temperature_Desired"],
    ["pGF_Corridor_Air_Sensor_Message", "pGF_Corridor_Air_Sensor_Temperature_Value", "pGF_Corridor_Air_Sensor_Humidity_Value", None, "pGF_Corridor_Temperature_Desired"],
    ["pGF_Utilityroom_Air_Sensor_Message", "pGF_Utilityroom_Air_Sensor_Temperature_Value", "pGF_Utilityroom_Air_Sensor_Humidity_Value", None, None],
    ["pGF_Garage_Air_Sensor_Message", "pGF_Garage_Air_Sensor_Temperature_Value", "pGF_Garage_Air_Sensor_Humidity_Value", None, None],
    ["pFF_Bedroom_Air_Sensor_Message", "pFF_Bedroom_Air_Sensor_Temperature_Value", "pFF_Bedroom_Air_Sensor_Humidity_Value", None, "pFF_Bedroom_Temperature_Desired"],
    ["pFF_Dressingroom_Air_Sensor_Message", "pFF_Dressingroom_Air_Sensor_Temperature_Value", "pFF_Dressingroom_Air_Sensor_Humidity_Value", "pGF_Dressingroom_Air_Sensor_CO2_Value", None],
    ["pFF_Fitnessroom_Air_Sensor_Message", "pFF_Fitnessroom_Air_Sensor_Temperature_Value", "pFF_Fitnessroom_Air_Sensor_Humidity_Value", None, "pFF_Fitnessroom_Temperature_Desired"],
    ["pFF_Makeuproom_Air_Sensor_Message", "pFF_Makeuproom_Air_Sensor_Temperature_Value", "pFF_Makeuproom_Air_Sensor_Humidity_Value", None, "pFF_Makeuproom_Temperature_Desired"],
    ["pFF_Bathroom_Air_Sensor_Message", "pFF_Bathroom_Air_Sensor_Temperature_Value", "pFF_Bathroom_Air_Sensor_Humidity_Value", None, "pFF_Bathroom_Temperature_Desired"],
    ["pFF_Corridor_Air_Sensor_Message", "pFF_Corridor_Air_Sensor_Temperature_Value", "pFF_Corridor_Air_Sensor_Humidity_Value", None, "pFF_Corridor_Temperature_Desired"],
    ["pFF_Attic_Air_Sensor_Message", "pFF_Attic_Air_Sensor_Temperature_Value", "pFF_Attic_Air_Sensor_Humidity_Value", None, None],

    ["pToolshed_Sensor_Message", "pToolshed_Sensor_Temperature_Value", "pToolshed_Sensor_Humidity_Value", None, None]
]

@rule()
class SensorTemperatureHumidityMessages:
    def __init__(self):
        self.triggers = []
        self.triggerMappings = {}
        self.updateTimer = {}
        for i, entry in enumerate(infoConfig):
            self.updateTimer[entry[0]] = None

            # *** TEMPERATURE ***
            # if exists, map raw temperature trigger
            temperaturItem = entry[1]

            # add temperature trigger and store infoData index
            self.triggerMappings[temperaturItem]=i
            self.triggers.append(ItemStateChangeTrigger(temperaturItem))

            # *** HUMIDITY ***
            # if exists, map raw humidity trigger
            humidityItem = entry[2]

            # add humidity trigger and store infoData index
            self.triggerMappings[humidityItem]=i
            self.triggers.append(ItemStateChangeTrigger(humidityItem))

            # *** TARGET VALUE ***
            if entry[3] is not None:
                self.triggerMappings[entry[3]]=i
                self.triggers.append(ItemStateChangeTrigger(entry[3]))

            # *** CO2 VALUE ***
            if entry[4] is not None:
                self.triggerMappings[entry[4]]=i
                self.triggers.append(ItemStateChangeTrigger(entry[4]))

    def updateInfoMessage(self, infoItem, temperatureItem, humidityItem, co2Item=None, temperatureTargetItem=None):
        #self.log.info(u">>>delay: {}".format(infoItem))
        
        msg = u"";
        if temperatureTargetItem is not None:
            msg = u"{}({}) ".format(msg,getItemState(temperatureTargetItem).format("%.1f"))

        #self.log.info(temperatureItem)
        msg = u"{}{} °C, ".format(msg,getItemState(temperatureItem).format("%.1f"))
        #self.log.info(humidityItem)
        msg = u"{}{} %".format(msg,getItemState(humidityItem).format("%.0f"))

        if co2Item is not None:
            msg = u"{}, {} ppm".format(msg,getItemState(co2Item).format("%d"))

        postUpdateIfChanged(infoItem, msg)
        
        self.updateTimer[infoItem] = None 

    def execute(self, module, input):
        itemName = input['event'].getItemName()

        data = infoConfig[ self.triggerMappings[itemName] ]
         
        #self.log.info(u">>>trigger: {} ".format(data[0]))

        # group 2 value updates into one message update
        # we have to delay 4 seconds, because sensor delay between 2 values is 3 seconds
        self.updateTimer[data[0]] = startTimer(self.log, 4, self.updateInfoMessage, args = [data[0], data[1], data[2], data[3], data[4]], oldTimer = self.updateTimer[data[0]], groupCount=2 ) 
        #self.updateInfoMessage()

