from shared.helper import rule, getNow, getItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged, startTimer
from core.triggers import CronTrigger, ItemStateChangeTrigger

infoConfig = [
    ["Air_GF_Livingroom_Message", "Temperature_GF_Livingroom", "Humidity_GF_Livingroom", "pGF_Livingroom_Heating_Temperature_Desired"],
    ["Air_GF_Boxroom_Message", "Temperature_GF_Boxroom", "Humidity_GF_Boxroom", None],
    ["Air_GF_Guestroom_Message", "Temperature_GF_Guestroom", "Humidity_GF_Guestroom", "pGF_Guestroom_Heating_Temperature_Desired"],
    ["Air_GF_Guesttoilet_Message", "Temperature_GF_Guesttoilet", "Humidity_GF_Guesttoilet", "pGF_Guesttoilet_Heating_Temperature_Desired"],
    ["Air_GF_Corridor_Message", "Temperature_GF_Corridor", "Humidity_GF_Corridor", "pGF_Corridor_Heating_Temperature_Desired"],
    ["Air_GF_Utilityroom_Message", "Temperature_GF_Utilityroom", "Humidity_GF_Utilityroom", None],
    ["Air_Garage_Message", "Temperature_Garage", "Humidity_Garage", None],
    ["Air_FF_Bedroom_Message", "Temperature_FF_Bedroom", "Humidity_FF_Bedroom", "pFF_Bedroom_Heating_Temperature_Desired"],
    ["Air_FF_Dressingroom_Message", "Temperature_FF_Dressingroom", "Humidity_FF_Dressingroom", None],
    ["Air_FF_Child1_Message", "Temperature_FF_Child1", "Humidity_FF_Child1", "pFF_Child1_Heating_Temperature_Desired"],
    ["Air_FF_Child2_Message", "Temperature_FF_Child2", "Humidity_FF_Child2", "pFF_Child2_Heating_Temperature_Desired"],
    ["Air_FF_Bathroom_Message", "Temperature_FF_Bathroom", "Humidity_FF_Bathroom", "pFF_Bathroom_Heating_Temperature_Desired"],
    ["Air_FF_Corridor_Message", "Temperature_FF_Corridor", "Humidity_FF_Corridor", "pFF_Corridor_Heating_Temperature_Desired"],
    ["Air_Attic_Message", "Temperature_Attic", "Humidity_Attic", None]
]

rawItems = {
    "Temperature_GF_Livingroom": ["Temperature_GF_Livingroom_Raw", -0.1, -1.4],
    "Humidity_GF_Livingroom": ["Humidity_GF_Livingroom_Raw", 7.4, 0.0],
    "Temperature_GF_Boxroom": ["Temperature_GF_Boxroom_Raw", -0.1, -1.4],
    "Humidity_GF_Boxroom": ["Humidity_GF_Boxroom_Raw", 1.9, 0.0],
    "Temperature_GF_Guestroom": ["Temperature_GF_Guestroom_Raw", -0.1, -1.4],
    "Humidity_GF_Guestroom": ["Humidity_GF_Guestroom_Raw", 2.6, 0.0],
    "Temperature_GF_Guesttoilet": ["Temperature_GF_Guesttoilet_Raw", 0.1, -1.4],
    "Humidity_GF_Guesttoilet": ["Humidity_GF_Guesttoilet_Raw", 0.7, 0.0],
    "Temperature_GF_Guesttoilet": ["Temperature_GF_Guesttoilet_Raw", 0.1, -1.4],
    "Humidity_GF_Guesttoilet": ["Humidity_GF_Guesttoilet_Raw", 0.7, 0.0],
    "Temperature_GF_Corridor": ["Temperature_GF_Corridor_Raw", 0.1, -1.4],
    "Humidity_GF_Corridor": ["Humidity_GF_Corridor_Raw", 4.0, 0.0],
    "Temperature_GF_Utilityroom": ["Temperature_GF_Utilityroom_Raw", -0.1, -1.4],
    "Humidity_GF_Utilityroom": ["Humidity_GF_Utilityroom_Raw", 1.7, 0.0],
    "Temperature_Garage": ["Temperature_Garage_Raw", 0.0, -1.4],
    "Humidity_Garage": ["Humidity_Garage_Raw", 3.6, 0.0],
    "Temperature_FF_Bedroom": ["Temperature_FF_Bedroom_Raw", -0.1, -1.4],
    "Humidity_FF_Bedroom": ["Humidity_FF_Bedroom_Raw", 5.2, 0.0],
    "Temperature_FF_Dressingroom": ["Temperature_FF_Dressingroom_Raw", 0.1, -1.4],
    "Humidity_FF_Dressingroom": ["Humidity_FF_Dressingroom_Raw", 0.4, 0.0],
    "Temperature_FF_Child1": ["Temperature_FF_Child1_Raw", 0.0, -1.4],
    "Humidity_FF_Child1": ["Humidity_FF_Child1_Raw", 1.1, 0.0],
    "Temperature_FF_Child2": ["Temperature_FF_Child2_Raw", 0.1, -1.4],
    "Humidity_FF_Child2": ["Humidity_FF_Child2_Raw", 2.8, 0.0],
    "Temperature_FF_Bathroom": ["Temperature_FF_Bathroom_Raw", 0.1, -1.4],
    "Humidity_FF_Bathroom": ["Humidity_FF_Bathroom_Raw", 5.3, 0.0],
    "Temperature_FF_Corridor": ["Temperature_FF_Corridor_Raw", 0.3, -1.4],
    "Humidity_FF_Corridor": ["Humidity_FF_Corridor_Raw", 2.5, 0.0],
    "Temperature_Attic": ["Temperature_Attic_Raw", -0.1, -0.9],
    "Humidity_Attic": ["Humidity_Attic_Raw", 1.9, 0.0]
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
            msg = u"{}({}) ".format(msg,getItemState(temperatureTargetItem).format("%.1f"))

        #self.log.info(temperatureItem)
        msg = u"{}{} °C, ".format(msg,getItemState(temperatureItem).format("%.1f"))
        #self.log.info(humidityItem)
        msg = u"{}{} %".format(msg,getItemState(humidityItem).format("%.1f"))

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

