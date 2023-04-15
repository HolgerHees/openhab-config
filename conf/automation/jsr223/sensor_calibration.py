from shared.helper import rule, getItemState, postUpdateIfChanged
from shared.triggers import ItemStateChangeTrigger

rawItems = {
    "pGF_Livingroom_Air_Sensor_Temperature_Raw": ["pGF_Livingroom_Air_Sensor_Temperature_Value", -1.3],             # 15.02.23
    "pGF_Livingroom_Air_Sensor_Humidity_Raw": ["pGF_Livingroom_Air_Sensor_Humidity_Value", 11.3],                   # 15.02.23
    "pGF_Boxroom_Air_Sensor_Temperature_Raw": ["pGF_Boxroom_Air_Sensor_Temperature_Value", -0.9],                   # 15.02.23
    "pGF_Boxroom_Air_Sensor_Humidity_Raw": ["pGF_Boxroom_Air_Sensor_Humidity_Value", 9.1],                          # 15.02.23
    "pGF_Workroom_Air_Sensor_Temperature_Raw": ["pGF_Workroom_Air_Sensor_Temperature_Value", -0.6],                 # 15.02.23
    "pGF_Workroom_Air_Sensor_Humidity_Raw": ["pGF_Workroom_Air_Sensor_Humidity_Value", 9.1],                        # 15.02.23
    "pGF_Guesttoilet_Air_Sensor_Temperature_Raw": ["pGF_Guesttoilet_Air_Sensor_Temperature_Value", -0.7],           # 15.02.23
    "pGF_Guesttoilet_Air_Sensor_Humidity_Raw": ["pGF_Guesttoilet_Air_Sensor_Humidity_Value", 5.6],                  # 15.02.23
    "pGF_Corridor_Air_Sensor_Temperature_Raw": ["pGF_Corridor_Air_Sensor_Temperature_Value", -1.0],                 # 15.02.23
    "pGF_Corridor_Air_Sensor_Humidity_Raw": ["pGF_Corridor_Air_Sensor_Humidity_Value", 8.4],                        # 15.02.23
    "pGF_Utilityroom_Air_Sensor_Temperature_Raw": ["pGF_Utilityroom_Air_Sensor_Temperature_Value", -0.4],           # 15.02.23
    "pGF_Utilityroom_Air_Sensor_Humidity_Raw": ["pGF_Utilityroom_Air_Sensor_Humidity_Value", 8.4],                  # 15.02.23
    "pGF_Garage_Air_Sensor_Temperature_Raw": ["pGF_Garage_Air_Sensor_Temperature_Value", -1.8],                     # 15.02.23
    "pGF_Garage_Air_Sensor_Humidity_Raw": ["pGF_Garage_Air_Sensor_Humidity_Value", 4.0],                            # 15.02.23
    "pFF_Bedroom_Air_Sensor_Temperature_Raw": ["pFF_Bedroom_Air_Sensor_Temperature_Value", -0.4],                   # 15.02.23
    "pFF_Bedroom_Air_Sensor_Humidity_Raw": ["pFF_Bedroom_Air_Sensor_Humidity_Value", 6.8],                          # 15.02.23
    "pFF_Dressingroom_Air_Sensor_Temperature_Raw": ["pFF_Dressingroom_Air_Sensor_Temperature_Value", -0.9],         # 15.02.23
    "pFF_Dressingroom_Air_Sensor_Humidity_Raw": ["pFF_Dressingroom_Air_Sensor_Humidity_Value", 8.0],                # 15.02.23
    "pFF_Fitnessroom_Air_Sensor_Temperature_Raw": ["pFF_Fitnessroom_Air_Sensor_Temperature_Value", -1.0],           # 15.02.23
    "pFF_Fitnessroom_Air_Sensor_Humidity_Raw": ["pFF_Fitnessroom_Air_Sensor_Humidity_Value", 9.6],                  # 15.02.23
    "pFF_Makeuproom_Air_Sensor_Temperature_Raw": ["pFF_Makeuproom_Air_Sensor_Temperature_Value", -0.6],             # 15.02.23
    "pFF_Makeuproom_Air_Sensor_Humidity_Raw": ["pFF_Makeuproom_Air_Sensor_Humidity_Value", 8.8],                    # 15.02.23
    "pFF_Bathroom_Air_Sensor_Temperature_Raw": ["pFF_Bathroom_Air_Sensor_Temperature_Value", -0.4],                 # 15.02.23
    "pFF_Bathroom_Air_Sensor_Humidity_Raw": ["pFF_Bathroom_Air_Sensor_Humidity_Value", 6.4],                        # 15.02.23
    "pFF_Corridor_Air_Sensor_Temperature_Raw": ["pFF_Corridor_Air_Sensor_Temperature_Value", 0.2],                  # 15.02.23
    "pFF_Corridor_Air_Sensor_Humidity_Raw": ["pFF_Corridor_Air_Sensor_Humidity_Value", 7.1],                        # 15.02.23
    "pFF_Attic_Air_Sensor_Temperature_Raw": ["pFF_Attic_Air_Sensor_Temperature_Value", -0.1],                       # 15.02.23
    "pFF_Attic_Air_Sensor_Humidity_Raw": ["pFF_Attic_Air_Sensor_Humidity_Value", 6.3],                              # 15.02.23

    "pGF_Livingroom_Humidifier_Humidity_Raw": ["pGF_Livingroom_Humidifier_Humidity_Value", 0.0],
}


@rule("sensor_calibration.py")
class CalibrationRule:
    def __init__(self):
        self.triggers = []
        for itemName in rawItems:
            self.triggers.append(ItemStateChangeTrigger(itemName))

            #self.calibrate(itemName, getItemState(itemName))

    def calibrate(self, itemName, itemState):
        config = rawItems[itemName]

        value = round(round(itemState.doubleValue(),1) + config[1], 1)
        postUpdateIfChanged(config[0], value)


    def execute(self, module, input):
        itemName = input['event'].getItemName()

        #self.log.info("{} {}".format(itemName, input['event'].getItemState()))

        self.calibrate(itemName, input['event'].getItemState() )

