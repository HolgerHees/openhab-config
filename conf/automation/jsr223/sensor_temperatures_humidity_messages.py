from shared.helper import rule, getNow, getItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged, startTimer
from core.triggers import CronTrigger, ItemStateChangeTrigger

infoConfig = [
    ["pGF_Livingroom_Air_Sensor_Message", "pGF_Livingroom_Air_Sensor_Temperature_Value", "pGF_Livingroom_Air_Sensor_Humidity_Value", "pGF_Livingroom_Heating_Temperature_Desired"],
    ["pGF_Boxroom_Air_Sensor_Message", "pGF_Boxroom_Air_Sensor_Temperature_Value", "pGF_Boxroom_Air_Sensor_Humidity_Value", None],
    ["pGF_Guestroom_Air_Sensor_Message", "pGF_Guestroom_Air_Sensor_Temperature_Value", "pGF_Guestroom_Air_Sensor_Humidity_Value", "pGF_Guestroom_Heating_Temperature_Desired"],
    ["pGF_Guesttoilet_Air_Sensor_Message", "pGF_Guesttoilet_Air_Sensor_Temperature_Value", "pGF_Guesttoilet_Air_Sensor_Humidity_Value", "pGF_Guesttoilet_Heating_Temperature_Desired"],
    ["pGF_Corridor_Air_Sensor_Message", "pGF_Corridor_Air_Sensor_Temperature_Value", "pGF_Corridor_Air_Sensor_Humidity_Value", "pGF_Corridor_Heating_Temperature_Desired"],
    ["pGF_Utilityroom_Air_Sensor_Message", "pGF_Utilityroom_Air_Sensor_Temperature_Value", "pGF_Utilityroom_Air_Sensor_Humidity_Value", None],
    ["pGF_Garage_Air_Sensor_Message", "pGF_Garage_Air_Sensor_Temperature_Value", "pGF_Garage_Air_Sensor_Humidity_Value", None],
    ["pFF_Bedroom_Air_Sensor_Message", "pFF_Bedroom_Air_Sensor_Temperature_Value", "pFF_Bedroom_Air_Sensor_Humidity_Value", "pFF_Bedroom_Heating_Temperature_Desired"],
    ["pFF_Dressingroom_Air_Sensor_Message", "pFF_Dressingroom_Air_Sensor_Temperature_Value", "pFF_Dressingroom_Air_Sensor_Humidity_Value", None],
    ["pFF_Child1_Air_Sensor_Message", "pFF_Child1_Air_Sensor_Temperature_Value", "pFF_Child1_Air_Sensor_Humidity_Value", "pFF_Child1_Heating_Temperature_Desired"],
    ["pFF_Child2_Air_Sensor_Message", "pFF_Child2_Air_Sensor_Temperature_Value", "pFF_Child2_Air_Sensor_Humidity_Value", "pFF_Child2_Heating_Temperature_Desired"],
    ["pFF_Bathroom_Air_Sensor_Message", "pFF_Bathroom_Air_Sensor_Temperature_Value", "pFF_Bathroom_Air_Sensor_Humidity_Value", "pFF_Bathroom_Heating_Temperature_Desired"],
    ["pFF_Corridor_Air_Sensor_Message", "pFF_Corridor_Air_Sensor_Temperature_Value", "pFF_Corridor_Air_Sensor_Humidity_Value", "pFF_Corridor_Heating_Temperature_Desired"],
    ["pFF_Attic_Air_Sensor_Message", "pFF_Attic_Air_Sensor_Temperature_Value", "pFF_Attic_Air_Sensor_Humidity_Value", None]
]

rawItems = {
    "pGF_Livingroom_Air_Sensor_Temperature_Value": ["pGF_Livingroom_Air_Sensor_Temperature_Raw", -0.1, -1.4],
    "pGF_Livingroom_Air_Sensor_Humidity_Value": ["pGF_Livingroom_Air_Sensor_Humidity_Raw", 7.4, 0.0],
    "pGF_Boxroom_Air_Sensor_Temperature_Value": ["pGF_Boxroom_Air_Sensor_Temperature_Raw", -0.1, -1.4],
    "pGF_Boxroom_Air_Sensor_Humidity_Value": ["pGF_Boxroom_Air_Sensor_Humidity_Raw", 1.9, 0.0],
    "pGF_Guestroom_Air_Sensor_Temperature_Value": ["pGF_Guestroom_Air_Sensor_Temperature_Raw", -0.1, -1.4],
    "pGF_Guestroom_Air_Sensor_Humidity_Value": ["pGF_Guestroom_Air_Sensor_Humidity_Raw", 2.6, 0.0],
    "pGF_Guesttoilet_Air_Sensor_Temperature_Value": ["pGF_Guesttoilet_Air_Sensor_Temperature_Raw", 0.1, -1.4],
    "pGF_Guesttoilet_Air_Sensor_Humidity_Value": ["pGF_Guesttoilet_Air_Sensor_Humidity_Raw", 0.7, 0.0],
    "pGF_Corridor_Air_Sensor_Temperature_Value": ["pGF_Corridor_Air_Sensor_Temperature_Raw", 0.1, -1.4],
    "pGF_Corridor_Air_Sensor_Humidity_Value": ["pGF_Corridor_Air_Sensor_Humidity_Raw", 4.0, 0.0],
    "pGF_Utilityroom_Air_Sensor_Temperature_Value": ["pGF_Utilityroom_Air_Sensor_Temperature_Raw", -0.1, -1.4],
    "pGF_Utilityroom_Air_Sensor_Humidity_Value": ["pGF_Utilityroom_Air_Sensor_Humidity_Raw", 1.7, 0.0],
    "pGF_Garage_Air_Sensor_Temperature_Value": ["pGF_Garage_Air_Sensor_Temperature_Raw", 0.0, -1.4],
    "pGF_Garage_Air_Sensor_Humidity_Value": ["pGF_Garage_Air_Sensor_Humidity_Raw", 3.6, 0.0],
    "pFF_Bedroom_Air_Sensor_Temperature_Value": ["pFF_Bedroom_Air_Sensor_Temperature_Raw", -0.1, -1.4],
    "pFF_Bedroom_Air_Sensor_Humidity_Value": ["pFF_Bedroom_Air_Sensor_Humidity_Raw", 5.2, 0.0],
    "pFF_Dressingroom_Air_Sensor_Temperature_Value": ["pFF_Dressingroom_Air_Sensor_Temperature_Raw", 0.1, -1.4],
    "pFF_Dressingroom_Air_Sensor_Humidity_Value": ["pFF_Dressingroom_Air_Sensor_Humidity_Raw", 0.4, 0.0],
    "pFF_Child1_Air_Sensor_Temperature_Value": ["pFF_Child1_Air_Sensor_Temperature_Raw", 0.0, -1.4],
    "pFF_Child1_Air_Sensor_Humidity_Value": ["pFF_Child1_Air_Sensor_Humidity_Raw", 1.1, 0.0],
    "pFF_Child2_Air_Sensor_Temperature_Value": ["pFF_Child2_Air_Sensor_Temperature_Raw", 0.1, -1.4],
    "pFF_Child2_Air_Sensor_Humidity_Value": ["pFF_Child2_Air_Sensor_Humidity_Raw", 2.8, 0.0],
    "pFF_Bathroom_Air_Sensor_Temperature_Value": ["pFF_Bathroom_Air_Sensor_Temperature_Raw", 0.1, -1.4],
    "pFF_Bathroom_Air_Sensor_Humidity_Value": ["pFF_Bathroom_Air_Sensor_Humidity_Raw", 5.3, 0.0],
    "pFF_Corridor_Air_Sensor_Temperature_Value": ["pFF_Corridor_Air_Sensor_Temperature_Raw", 0.3, -1.4],
    "pFF_Corridor_Air_Sensor_Humidity_Value": ["pFF_Corridor_Air_Sensor_Humidity_Raw", 2.5, 0.0],
    "pFF_Attic_Air_Sensor_Temperature_Value": ["pFF_Attic_Air_Sensor_Temperature_Raw", -0.1, -0.9],
    "pFF_Attic_Air_Sensor_Humidity_Value": ["pFF_Attic_Air_Sensor_Humidity_Raw", 1.9, 0.0]
}


@rule("sensor_temperatures_humidity_messages.py")
class InfoValueRule:
    def __init__(self):
        self.triggers = []
        self.triggerMappings = {}
        self.rawMappings = {}
        self.updateTimer = {}
        for i, entry in enumerate(infoConfig):
            self.updateTimer[entry[0]] = None

            # *** TEMPERATURE ***
            # if exists, map raw temperature trigger
            temperaturItem = entry[1]
            if temperaturItem in rawItems:
                _temperaturItem = temperaturItem
                temperaturItem = rawItems[temperaturItem][0]
                self.rawMappings[temperaturItem]=_temperaturItem

            # add temperature trigger and store infoData index
            self.triggerMappings[temperaturItem]=i
            self.triggers.append(ItemStateChangeTrigger(temperaturItem))

            # *** HUMIDITY ***
            # if exists, map raw humidity trigger
            humidityItem = entry[2]
            if humidityItem in rawItems:
                _humidityItem = humidityItem
                humidityItem = rawItems[humidityItem][0]
                self.rawMappings[humidityItem]=_humidityItem

            # add humidity trigger and store infoData index
            self.triggerMappings[humidityItem]=i
            self.triggers.append(ItemStateChangeTrigger(humidityItem))

            # *** TARGET VALUE ***
            if entry[3] is not None:
                self.triggerMappings[entry[3]]=i
                self.triggers.append(ItemStateChangeTrigger(entry[3]))

    def processRawValue(self, valueItem, rawState, calibrationDiff, finalDiff):
        value = round(round(rawState.doubleValue(),1) + calibrationDiff + finalDiff, 1)
        return postUpdateIfChanged(valueItem, value)

    def updateInfoMessage(self, infoItem, temperatureItem, humidityItem, temperatureTargetItem=None):
        #self.log.info(u">>>delay: {}".format(infoItem))
        
        msg = u"";
        if temperatureTargetItem is not None:
            msg = u"{}({}) ".format(msg,str(getItemState(temperatureTargetItem)).format("%.1f"))

        #self.log.info(temperatureItem)
        msg = u"{}{} °C, ".format(msg,str(getItemState(temperatureItem)).format("%.1f"))
        #self.log.info(humidityItem)
        msg = u"{}{} %".format(msg,str(getItemState(humidityItem)).format("%.1f"))

        postUpdateIfChanged(infoItem, msg)
        
        self.updateTimer[infoItem] = None 

    def execute(self, module, input):
        itemName = input['event'].getItemName()

        # was it a raw trigger?
        if itemName in self.rawMappings:
            rawItemName = self.rawMappings[itemName]
            entry = rawItems[ rawItemName ]

            if not self.processRawValue( rawItemName, input['event'].getItemState(), entry[1], entry[2]):
                return

        data = infoConfig[ self.triggerMappings[itemName] ]
         
        #self.log.info(u">>>trigger: {} ".format(data[0]))

        # group 2 value updates into one message update
        # we have to delay 4 seconds, because sensor delay between 2 values is 3 seconds
        self.updateTimer[data[0]] = startTimer(self.log, 4, self.updateInfoMessage, args = [data[0], data[1], data[2], data[3]], oldTimer = self.updateTimer[data[0]], groupCount=2 ) 
        #self.updateInfoMessage()

