from marvin.helper import rule, getItemState, sendCommand, postUpdateIfChanged
from core.triggers import ItemCommandTrigger, ItemStateChangeTrigger
from org.eclipse.smarthome.core.types import UnDefType

@rule("lights_indoor_livingroom_control.py")
class CeilingRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Lights_FF_Livingroom_Ceiling")]

    def execute(self, module, input):
        sendCommand("Light_FF_Livingroom_Diningtable", input["command"])
        sendCommand("Light_FF_Livingroom_Couch", input["command"])


@rule("lights_indoor_livingroom_control.py")
class CeilingBackwardRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Light_FF_Livingroom_Diningtable"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Couch")
        ]

    def execute(self, module, input):
        value = 0
        
        # check for UnDefType. Happens if I increase or decrease dimming value manually
        if type(getItemState("Light_FF_Livingroom_Diningtable")) is not UnDefType and getItemState("Light_FF_Livingroom_Diningtable").intValue() > value:
            value = getItemState("Light_FF_Livingroom_Diningtable").intValue()
        # check for UnDefType. Happens if I increase or decrease dimming value manually
        if type(getItemState("Light_FF_Livingroom_Couch")) is not UnDefType and getItemState("Light_FF_Livingroom_Couch").intValue() > value:
            value = getItemState("Light_FF_Livingroom_Couch").intValue()

        postUpdateIfChanged("Lights_FF_Livingroom_Ceiling", value)


@rule("lights_indoor_livingroom_control.py")
class HueBrightnessRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Light_FF_Livingroom_Hue_Brightness")]

    def execute(self, module, input):
        sendCommand("Light_FF_Livingroom_Hue_Brightness1", input["command"])
        sendCommand("Light_FF_Livingroom_Hue_Brightness2", input["command"])
        sendCommand("Light_FF_Livingroom_Hue_Brightness3", input["command"])
        sendCommand("Light_FF_Livingroom_Hue_Brightness4", input["command"])
        sendCommand("Light_FF_Livingroom_Hue_Brightness5", input["command"])


@rule("lights_indoor_livingroom_control.py")
class HueBrightnessBackwardRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Brightness1"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Brightness2"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Brightness3"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Brightness4"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Brightness5")
        ]

    def execute(self, module, input):
        value = 0
        if getItemState("Light_FF_Livingroom_Hue_Brightness1").intValue() > value:
            value = getItemState("Light_FF_Livingroom_Hue_Brightness1").intValue()
        if getItemState("Light_FF_Livingroom_Hue_Brightness2").intValue() > value:
            value = getItemState("Light_FF_Livingroom_Hue_Brightness2").intValue()
        if getItemState("Light_FF_Livingroom_Hue_Brightness3").intValue() > value:
            value = getItemState("Light_FF_Livingroom_Hue_Brightness3").intValue()
        if getItemState("Light_FF_Livingroom_Hue_Brightness4").intValue() > value:
            value = getItemState("Light_FF_Livingroom_Hue_Brightness4").intValue()
        if getItemState("Light_FF_Livingroom_Hue_Brightness5").intValue() > value:
            value = getItemState("Light_FF_Livingroom_Hue_Brightness5").intValue()

        postUpdateIfChanged("Light_FF_Livingroom_Hue_Brightness", value)


@rule("lights_indoor_livingroom_control.py")
class HueColorRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Light_FF_Livingroom_Hue_Color")]

    def execute(self, module, input):
        sendCommand("Light_FF_Livingroom_Hue_Color1", input["command"])
        sendCommand("Light_FF_Livingroom_Hue_Color2", input["command"])
        sendCommand("Light_FF_Livingroom_Hue_Color3", input["command"])
        sendCommand("Light_FF_Livingroom_Hue_Color4", input["command"])
        sendCommand("Light_FF_Livingroom_Hue_Color5", input["command"])


@rule("lights_indoor_livingroom_control.py")
class HueColorBackwardRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Color1"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Color2"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Color3"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Color4"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Hue_Color5")
        ]

    def execute(self, module, input):
        state = getItemState("Light_FF_Livingroom_Hue_Color1")
        if getItemState("Light_FF_Livingroom_Hue_Color2") == state \
                and getItemState("Light_FF_Livingroom_Hue_Color3") == state \
                and getItemState("Light_FF_Livingroom_Hue_Color4") == state \
                and getItemState("Light_FF_Livingroom_Hue_Color5") == state:
            postUpdateIfChanged("Light_FF_Livingroom_Hue_Color", state)
