from openhab import rule, Registry, Timer
from openhab.triggers import ItemStateChangeTrigger


info_config = [
    ["pGF_Livingroom_Air_Sensor_Message", "pGF_Livingroom_Air_Sensor_Temperature_Value", "pGF_Livingroom_Air_Sensor_Humidity_Value", "pGF_Livingroom_Air_Sensor_CO2_Value", "pGF_Livingroom_Temperature_Desired"],
    ["pGF_Boxroom_Air_Sensor_Message", "pGF_Boxroom_Air_Sensor_Temperature_Value", "pGF_Boxroom_Air_Sensor_Humidity_Value", "pGF_Boxroom_Air_Sensor_CO2_Value", None],
    ["pGF_Workroom_Air_Sensor_Message", "pGF_Workroom_Air_Sensor_Temperature_Value", "pGF_Workroom_Air_Sensor_Humidity_Value", None, "pGF_Workroom_Temperature_Desired"],
    ["pGF_Guesttoilet_Air_Sensor_Message", "pGF_Guesttoilet_Air_Sensor_Temperature_Value", "pGF_Guesttoilet_Air_Sensor_Humidity_Value", None, "pGF_Guesttoilet_Temperature_Desired"],
    ["pGF_Corridor_Air_Sensor_Message", "pGF_Corridor_Air_Sensor_Temperature_Value", "pGF_Corridor_Air_Sensor_Humidity_Value", None, "pGF_Corridor_Temperature_Desired"],
    ["pGF_Utilityroom_Air_Sensor_Message", "pGF_Utilityroom_Air_Sensor_Temperature_Value", "pGF_Utilityroom_Air_Sensor_Humidity_Value", None, None],
    ["pGF_Garage_Air_Sensor_Message", "pGF_Garage_Air_Sensor_Temperature_Value", "pGF_Garage_Air_Sensor_Humidity_Value", None, None],
    ["pFF_Bedroom_Air_Sensor_Message", "pFF_Bedroom_Air_Sensor_Temperature_Value", "pFF_Bedroom_Air_Sensor_Humidity_Value", "pFF_Bedroom_Air_Sensor_CO2_Value", "pFF_Bedroom_Temperature_Desired"],
    ["pFF_Dressingroom_Air_Sensor_Message", "pFF_Dressingroom_Air_Sensor_Temperature_Value", "pFF_Dressingroom_Air_Sensor_Humidity_Value", None, None],
    ["pFF_Fitnessroom_Air_Sensor_Message", "pFF_Fitnessroom_Air_Sensor_Temperature_Value", "pFF_Fitnessroom_Air_Sensor_Humidity_Value", None, "pFF_Fitnessroom_Temperature_Desired"],
    ["pFF_Makeuproom_Air_Sensor_Message", "pFF_Makeuproom_Air_Sensor_Temperature_Value", "pFF_Makeuproom_Air_Sensor_Humidity_Value", None, "pFF_Makeuproom_Temperature_Desired"],
    ["pFF_Bathroom_Air_Sensor_Message", "pFF_Bathroom_Air_Sensor_Temperature_Value", "pFF_Bathroom_Air_Sensor_Humidity_Value", None, "pFF_Bathroom_Temperature_Desired"],
    ["pFF_Corridor_Air_Sensor_Message", "pFF_Corridor_Air_Sensor_Temperature_Value", "pFF_Corridor_Air_Sensor_Humidity_Value", None, "pFF_Corridor_Temperature_Desired"],
    ["pFF_Attic_Air_Sensor_Message", "pFF_Attic_Air_Sensor_Temperature_Value", "pFF_Attic_Air_Sensor_Humidity_Value", None, None],

    ["pToolshed_Sensor_Message", "pToolshed_Sensor_Temperature_Value", "pToolshed_Sensor_Humidity_Value", None, None]
]


@rule()
class Main:
    def __init__(self):
        self.trigger_mappings = {}
        self.update_timer = {}

    def buildTriggers(self):
        triggers = []
        for i, entry in enumerate(info_config):
            self.update_timer[entry[0]] = None

            # *** TEMPERATURE ***
            # if exists, map raw temperature trigger
            temperaturItem = entry[1]

            # add temperature trigger and store infoData index
            self.trigger_mappings[temperaturItem]=i
            triggers.append(ItemStateChangeTrigger(temperaturItem))

            # *** HUMIDITY ***
            # if exists, map raw humidity trigger
            humidity_item = entry[2]

            # add humidity trigger and store infoData index
            self.trigger_mappings[humidity_item]=i
            triggers.append(ItemStateChangeTrigger(humidity_item))

            # *** TARGET VALUE ***
            if entry[3] is not None:
                self.trigger_mappings[entry[3]]=i
                triggers.append(ItemStateChangeTrigger(entry[3]))

            # *** CO2 VALUE ***
            if entry[4] is not None:
                self.trigger_mappings[entry[4]]=i
                triggers.append(ItemStateChangeTrigger(entry[4]))

        return triggers

    def updateInfoMessage(self, info_item, temperature_item, humidity_item, co2_item=None, temperature_target_item=None):
        #self.logger.info(">>>delay: {}".format(info_item))
        
        msg = "";
        if temperature_target_item is not None:
            msg = "{}({}) ".format(msg, Registry.getItemState(temperature_target_item).format("%.1f"))

        #self.logger.info(temperature_item)
        msg = "{}{} °C, ".format(msg, Registry.getItemState(temperature_item).format("%.1f"))
        #self.logger.info(humidity_item)
        msg = "{}{} %".format(msg, Registry.getItemState(humidity_item).format("%.0f"))

        if co2_item is not None:
            msg = "{}, {} ppm".format(msg, Registry.getItemState(co2_item).format("%d"))

        Registry.getItem(info_item).postUpdateIfDifferent(msg)
        
        self.update_timer[info_item] = None

    def execute(self, module, input):
        itemName = input['event'].getItemName()

        data = info_config[ self.trigger_mappings[itemName] ]
         
        #self.logger.info(">>>trigger: {} ".format(data[0]))

        # group 2 value updates into one message update
        # we have to delay 4 seconds, because sensor delay between 2 values is 3 seconds
        self.update_timer[data[0]] = Timer.createTimeout(4, self.updateInfoMessage, args = [data[0], data[1], data[2], data[3], data[4]], old_timer = self.update_timer[data[0]], max_count=2 )
        #self.updateInfoMessage()

