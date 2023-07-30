from shared.helper import rule, sendCommand, getItemState
from shared.triggers import ItemStateChangeTrigger, ItemStateUpdateTrigger


@rule()
class LightsIndoorBedroomControl:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pFF_Bedroom_Switches_Long_Pressed_Left_State", state="ON"),
            ItemStateChangeTrigger("pFF_Bedroom_Switches_Long_Pressed_Right_State", state="ON")
        ]

    def execute(self, module, input):
        sendCommand("pOther_Scene4", ON)

@rule()
class LightsIndoorBedroomLeftControl:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("pFF_Bedroom_Light_Hue_Left_Switch", state="ON")
        ]

    def execute(self, module, input):
        self.log.info("{}".format(getItemState("pFF_Bedroom_Light_Hue_Left_Color")))

        if getItemState("pFF_Bedroom_Light_Hue_Left_Color").as(OnOffType) == OnOffType.ON:
            sendCommand("pFF_Bedroom_Light_Hue_Left_Color",100)
        else:
            sendCommand("pFF_Bedroom_Light_Hue_Left_Color",0)
            
@rule()
class LightsIndoorBedroomRightControl:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("pFF_Bedroom_Light_Hue_Right_Switch", state="ON")
        ]

    def execute(self, module, input):
        self.log.info("{}".format(getItemState("pFF_Bedroom_Light_Hue_Right_Color")))

        if getItemState("pFF_Bedroom_Light_Hue_Right_Color").as(OnOffType) == OnOffType.ON:
            sendCommand("pFF_Bedroom_Light_Hue_Right_Color",100)
        else:
            sendCommand("pFF_Bedroom_Light_Hue_Right_Color",0)
