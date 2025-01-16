from openhab import rule, logger, Registry
from openhab.triggers import ItemStateChangeTrigger, ItemStateUpdateTrigger


@rule(
    triggers = [
        ItemStateChangeTrigger("pFF_Bedroom_Switches_Long_Pressed_Left_State", state="ON"),
        ItemStateChangeTrigger("pFF_Bedroom_Switches_Long_Pressed_Right_State", state="ON")
    ]
)
class Control:
    def execute(self, module, input):
        Registry.getItem("pOther_Scene4").sendCommand(ON)

@rule(
    triggers = [
        ItemStateUpdateTrigger("pFF_Bedroom_Light_Hue_Left_Switch", state="ON")
    ]
)
class LeftControl:
    def execute(self, module, input):
        if Registry.getItemState("pFF_Bedroom_Light_Hue_Left_Color").getBrightness().intValue() > 0:
            Registry.getItem("pFF_Bedroom_Light_Hue_Left_Color").sendCommand(0)
        else:
            Registry.getItem("pFF_Bedroom_Light_Hue_Left_Color").sendCommand(100)
            
@rule(
    triggers = [
        ItemStateUpdateTrigger("pFF_Bedroom_Light_Hue_Right_Switch", state="ON")
    ]
)
class RightControl:
    def execute(self, module, input):
        if Registry.getItemState("pFF_Bedroom_Light_Hue_Right_Color").getBrightness().intValue() > 0:
            Registry.getItem("pFF_Bedroom_Light_Hue_Right_Color").sendCommand(0)
        else:
            Registry.getItem("pFF_Bedroom_Light_Hue_Right_Color").sendCommand(100)
