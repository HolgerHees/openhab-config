from marvin.helper import rule, getItemState, postUpdateIfChanged
from openhab.triggers import ItemStateChangeTrigger


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
            soilMoistSensor1 = getItemState("SoilMoistSensor1").intValue()
            soilMoistSensor2 = getItemState("SoilMoistSensor2").intValue()
            soilMoistSensor3 = getItemState("SoilMoistSensor3").intValue()
            soilMoistSensor4 = getItemState("SoilMoistSensor4").intValue()

            if soilMoistSensor1 < 380 or soilMoistSensor2 < 380 or soilMoistSensor3 < 380 or soilMoistSensor4 < 380:
                msg = u"Jetzt Giessen"
            elif soilMoistSensor1 < 400 or soilMoistSensor2 < 400 or soilMoistSensor3 < 400 or soilMoistSensor4 < 400:
                msg = u"Giessen"
            else:
                msg = u"Feucht genug"

        postUpdateIfChanged("PlantSensorInfo", msg)
