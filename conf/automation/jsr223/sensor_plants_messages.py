from shared.helper import rule, getItemState, postUpdateIfChanged
from shared.triggers import ItemStateChangeTrigger, CronTrigger


@rule()
class SensorPlantsMessagesSummery:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Watering_Info")
        ]

    def execute(self, module, input):
        state = getItemState("pIndoor_Plant_Sensor_Watering_Info").toString()

        if state != "Feucht genug" and state != "Nicht aktiv":
            msg = state
        else:
            msg = u"Alles ok"

        postUpdateIfChanged("pIndoor_Plant_Sensor_Main_Info", msg)


@rule()
class SensorPlantsMessagesDetail:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_State1"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_State2"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_State3"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_State4")
        ]

    def execute(self, module, input):
        msg = u"Nicht aktiv"

        if getItemState("pOther_Manual_State_Auto_Attic_Light").intValue() != 1:
            soilMoistSensor1 = getItemState("pIndoor_Plant_Sensor_Device_State1").intValue() if getItemState("pIndoor_Plant_Sensor_Device_Enabled1") == ON else 1000
            soilMoistSensor2 = getItemState("pIndoor_Plant_Sensor_Device_State2").intValue() if getItemState("pIndoor_Plant_Sensor_Device_Enabled2") == ON else 1000
            soilMoistSensor3 = getItemState("pIndoor_Plant_Sensor_Device_State3").intValue() if getItemState("pIndoor_Plant_Sensor_Device_Enabled3") == ON else 1000
            soilMoistSensor4 = getItemState("pIndoor_Plant_Sensor_Device_State4").intValue() if getItemState("pIndoor_Plant_Sensor_Device_Enabled4") == ON else 1000

            if soilMoistSensor1 < 380 or soilMoistSensor2 < 380 or soilMoistSensor3 < 380 or soilMoistSensor4 < 380:
                msg = u"Jetzt Giessen"
            elif soilMoistSensor1 < 400 or soilMoistSensor2 < 400 or soilMoistSensor3 < 400 or soilMoistSensor4 < 400:
                msg = u"Giessen"
            else:
                msg = u"Feucht genug"

        postUpdateIfChanged("pIndoor_Plant_Sensor_Watering_Info", msg)

@rule()
class SensorPlantsMessagesEnabled:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_Enabled1"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_Enabled2"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_Enabled3"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_Enabled4"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_Enabled5"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Device_Enabled6")
        ]

    def execute(self, module, input):
        active = []
        if getItemState("pIndoor_Plant_Sensor_Device_Enabled1") == ON:
            active.append("1")
        if getItemState("pIndoor_Plant_Sensor_Device_Enabled2") == ON:
            active.append("2")
        if getItemState("pIndoor_Plant_Sensor_Device_Enabled3") == ON:
            active.append("3")
        if getItemState("pIndoor_Plant_Sensor_Device_Enabled4") == ON:
            active.append("4")
        if getItemState("pIndoor_Plant_Sensor_Device_Enabled5") == ON:
            active.append("5")
        if getItemState("pIndoor_Plant_Sensor_Device_Enabled6") == ON:
            active.append("6")
        postUpdateIfChanged("pIndoor_Plant_Sensor_Activation_Info", u", ".join(active)) 
            
