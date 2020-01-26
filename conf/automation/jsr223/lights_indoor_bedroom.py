from custom.helper import rule, sendCommand, getItemState
from core.triggers import ItemStateChangeTrigger, ItemStateUpdateTrigger


@rule("lights_indoor_bedroom_control.py")
class LightsIndoorBedroomControlRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Light_SF_Bedroom_Left_Long_Pressed", state="ON"),
            ItemStateChangeTrigger("Light_SF_Bedroom_Right_Long_Pressed", state="ON")
        ]

    def execute(self, module, input):
        sendCommand("Scene4", ON)

@rule("lights_indoor_bedroom_left_control.py")
class LightsIndoorBedroomLeftControlRule:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("Light_SF_Bedroom_Left", state="ON")
        ]

    def execute(self, module, input):
        if getItemState("Light_SF_Bedroom_Left_Hue_Brightness").intValue() == 0:
            sendCommand("Light_SF_Bedroom_Left_Hue_Brightness",100)
        else:
            sendCommand("Light_SF_Bedroom_Left_Hue_Brightness",0)
            
@rule("lights_indoor_bedroom_right_control.py")
class LightsIndoorBedroomRightControlRule:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("Light_SF_Bedroom_Right", state="ON")
        ]

    def execute(self, module, input):
        if getItemState("Light_SF_Bedroom_Right_Hue_Brightness").intValue() == 0:
            sendCommand("Light_SF_Bedroom_Right_Hue_Brightness",100)
        else:
            sendCommand("Light_SF_Bedroom_Right_Hue_Brightness",0)
