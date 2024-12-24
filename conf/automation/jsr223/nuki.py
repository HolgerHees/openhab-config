from shared.helper import rule, getItemState, NotificationHelper

@rule()
class SensorWeatherstationBatteryDetail:
    def __init__(self):
        triggers = [
            ItemStateChangeTrigger("pGF_Corridor_Lock_Battery_Critical")
        ]

    def execute(self, module, input):
        if input['event'].getItemState() == ON:
            postUpdateIfChanged("pGF_Corridor_Lock_State_Device_Info", "Batterie")
        else:
            postUpdateIfChanged("pGF_Corridor_Lock_State_Device_Info", "Alles ok")
