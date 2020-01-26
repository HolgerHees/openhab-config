from custom.helper import rule, getItemState, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger


@rule("scene_plant_messages.py")
class SummeryRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("PlantSensorInfo")]

    def execute(self, module, input):
        state = getItemState("PlantSensorInfo").toString()

        if state != "Feucht genug" and state != "Nicht aktiv":
            msg = state
        else:
            msg = u"Alles normal"

        postUpdateIfChanged("SensorInfo", msg)


@rule("scene_plant_messages.py")
class DetailRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("SoilMoistSensor1"),
            ItemStateChangeTrigger("SoilMoistSensor2"),
            ItemStateChangeTrigger("SoilMoistSensor3"),
            ItemStateChangeTrigger("SoilMoistSensor4")
        ]

    def execute(self, module, input):
        msg = u"Nicht aktiv"

        if getItemState("Auto_Attic_Light").intValue() != 1:
            soilMoistSensor1 = getItemState("SoilMoistSensor1").intValue() if getItemState("SoilMoistSensor1Enabled") == ON else 1000
            soilMoistSensor2 = getItemState("SoilMoistSensor2").intValue() if getItemState("SoilMoistSensor2Enabled") == ON else 1000
            soilMoistSensor3 = getItemState("SoilMoistSensor3").intValue() if getItemState("SoilMoistSensor3Enabled") == ON else 1000
            soilMoistSensor4 = getItemState("SoilMoistSensor4").intValue() if getItemState("SoilMoistSensor4Enabled") == ON else 1000

            if soilMoistSensor1 < 380 or soilMoistSensor2 < 380 or soilMoistSensor3 < 380 or soilMoistSensor4 < 380:
                msg = u"Jetzt Giessen"
            elif soilMoistSensor1 < 400 or soilMoistSensor2 < 400 or soilMoistSensor3 < 400 or soilMoistSensor4 < 400:
                msg = u"Giessen"
            else:
                msg = u"Feucht genug"

        postUpdateIfChanged("PlantSensorInfo", msg)

@rule("scene_plant_messages.py")
class EnabledRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("SoilMoistSensor1Enabled"),
            ItemStateChangeTrigger("SoilMoistSensor2Enabled"),
            ItemStateChangeTrigger("SoilMoistSensor3Enabled"),
            ItemStateChangeTrigger("SoilMoistSensor4Enabled"),
            ItemStateChangeTrigger("SoilMoistSensor5Enabled"),
            ItemStateChangeTrigger("SoilMoistSensor6Enabled")
        ]

    def execute(self, module, input):
        active = []
        if getItemState("SoilMoistSensor1Enabled") == ON:
            active.append("1")
        if getItemState("SoilMoistSensor2Enabled") == ON:
            active.append("2")
        if getItemState("SoilMoistSensor3Enabled") == ON:
            active.append("3")
        if getItemState("SoilMoistSensor4Enabled") == ON:
            active.append("4")
        if getItemState("SoilMoistSensor5Enabled") == ON:
            active.append("5")
        if getItemState("SoilMoistSensor6Enabled") == ON:
            active.append("6")
        postUpdateIfChanged("SoilMoistSensorInfo", u", ".join(active)) 
            
