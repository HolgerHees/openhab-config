from shared.helper import rule, getItemState, postUpdateIfChanged
from shared.triggers import ItemStateChangeTrigger

rawItems = {
    "pGF_Livingroom_Air_Sensor_Temperature_Raw": ["pGF_Livingroom_Air_Sensor_Temperature_Value", -1.2],             # 11.02.23
    "pGF_Livingroom_Air_Sensor_Humidity_Raw": ["pGF_Livingroom_Air_Sensor_Humidity_Value", 7.4],
    "pGF_Boxroom_Air_Sensor_Temperature_Raw": ["pGF_Boxroom_Air_Sensor_Temperature_Value", -0.6],                   # 11.02.23
    "pGF_Boxroom_Air_Sensor_Humidity_Raw": ["pGF_Boxroom_Air_Sensor_Humidity_Value", 1.9],
    "pGF_Workroom_Air_Sensor_Temperature_Raw": ["pGF_Workroom_Air_Sensor_Temperature_Value", -1.5],
    "pGF_Workroom_Air_Sensor_Humidity_Raw": ["pGF_Workroom_Air_Sensor_Humidity_Value", 2.6],
    "pGF_Guesttoilet_Air_Sensor_Temperature_Raw": ["pGF_Guesttoilet_Air_Sensor_Temperature_Value", -0.3],           # 11.02.23
    "pGF_Guesttoilet_Air_Sensor_Humidity_Raw": ["pGF_Guesttoilet_Air_Sensor_Humidity_Value", 0.7],
    "pGF_Corridor_Air_Sensor_Temperature_Raw": ["pGF_Corridor_Air_Sensor_Temperature_Value", -1.1],                 # 11.02.23
    "pGF_Corridor_Air_Sensor_Humidity_Raw": ["pGF_Corridor_Air_Sensor_Humidity_Value", 4.0],
    "pGF_Utilityroom_Air_Sensor_Temperature_Raw": ["pGF_Utilityroom_Air_Sensor_Temperature_Value", -0.9],           # 11.02.23
    "pGF_Utilityroom_Air_Sensor_Humidity_Raw": ["pGF_Utilityroom_Air_Sensor_Humidity_Value", 1.7],
    "pGF_Garage_Air_Sensor_Temperature_Raw": ["pGF_Garage_Air_Sensor_Temperature_Value", -1.4],
    "pGF_Garage_Air_Sensor_Humidity_Raw": ["pGF_Garage_Air_Sensor_Humidity_Value", 3.6],
    "pFF_Bedroom_Air_Sensor_Temperature_Raw": ["pFF_Bedroom_Air_Sensor_Temperature_Value", -1.5],
    "pFF_Bedroom_Air_Sensor_Humidity_Raw": ["pFF_Bedroom_Air_Sensor_Humidity_Value", 5.2],
    "pFF_Dressingroom_Air_Sensor_Temperature_Raw": ["pFF_Dressingroom_Air_Sensor_Temperature_Value", -1.3],
    "pFF_Dressingroom_Air_Sensor_Humidity_Raw": ["pFF_Dressingroom_Air_Sensor_Humidity_Value", 0.4],
    "pFF_Fitnessroom_Air_Sensor_Temperature_Raw": ["pFF_Fitnessroom_Air_Sensor_Temperature_Value", -1.4],
    "pFF_Fitnessroom_Air_Sensor_Humidity_Raw": ["pFF_Fitnessroom_Air_Sensor_Humidity_Value", 1.1],
    "pFF_Makeuproom_Air_Sensor_Temperature_Raw": ["pFF_Makeuproom_Air_Sensor_Temperature_Value", -1.3],
    "pFF_Makeuproom_Air_Sensor_Humidity_Raw": ["pFF_Makeuproom_Air_Sensor_Humidity_Value", 2.8],
    "pFF_Bathroom_Air_Sensor_Temperature_Raw": ["pFF_Bathroom_Air_Sensor_Temperature_Value", -1.3],
    "pFF_Bathroom_Air_Sensor_Humidity_Raw": ["pFF_Bathroom_Air_Sensor_Humidity_Value", 5.3],
    "pFF_Corridor_Air_Sensor_Temperature_Raw": ["pFF_Corridor_Air_Sensor_Temperature_Value", -1.1],
    "pFF_Corridor_Air_Sensor_Humidity_Raw": ["pFF_Corridor_Air_Sensor_Humidity_Value", 2.5],
    "pFF_Attic_Air_Sensor_Temperature_Raw": ["pFF_Attic_Air_Sensor_Temperature_Value", -1.0],
    "pFF_Attic_Air_Sensor_Humidity_Raw": ["pFF_Attic_Air_Sensor_Humidity_Value", 1.9],

    "pGF_Livingroom_Humidifier_Humidity_Raw": ["pGF_Livingroom_Humidifier_Humidity_Value", 0.0],
}


@rule("sensor_calibration.py")
class CalibrationRule:
    def __init__(self):
        self.triggers = []
        for rawItem in rawItems:
            self.triggers.append(ItemStateChangeTrigger(rawItem))

    def execute(self, module, input):
        itemName = input['event'].getItemName()

        config = rawItems[itemName]

        value = round(round(input['event'].getItemState().doubleValue(),1) + config[1], 1)
        postUpdateIfChanged(config[0], value)
