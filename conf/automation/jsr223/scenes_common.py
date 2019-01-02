from marvin.helper import rule, getItem, getItemState, sendCommand, postUpdate
from core.triggers import ItemCommandTrigger


@rule("scenes_common.py")
class Scene1Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Scene1","ON")]

    def execute(self, module, input):
        sendCommand("Light_FF_Livingroom_Hue_Brightness", 60)

        states = [OFF, PercentType.ZERO]

        for child in getItem("Lights_FF").getAllMembers():
            if child.getState() not in states and child.getName() != "Light_FF_Livingroom_Hue_Brightness":
                sendCommand(child, OFF)

        for child in getItem("Lights_SF").getAllMembers():
            if child.getState() not in states:
                sendCommand(child, OFF)

        postUpdate("Scene1", OFF)


@rule("scenes_common.py")
class Scene2Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Scene2","ON")]

    def execute(self, module, input):
        sendCommand("Light_FF_Floor_Ceiling", ON)
        sendCommand("Light_SF_Bathroom_Ceiling", ON)
        sendCommand("Light_SF_Bathroom_Mirror", ON)
        sendCommand("Light_SF_Bedroom_Ceiling", ON)

        postUpdate("Scene2", OFF)


@rule("scenes_common.py")
class Scene3Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Scene3","ON")]

    def execute(self, module, input):
        sendCommand("Light_FF_Floor_Hue_Brightness", 60)
        sendCommand("Light_SF_Bathroom_Mirror", ON)
        sendCommand("Light_SF_Bedroom_Right", ON)

        states = [OFF, PercentType.ZERO]

        for child in getItem("Lights_FF").getAllMembers():
            if child.getState() not in states and child.getName() != "Light_FF_Floor_Hue_Brightness":
                sendCommand(child, OFF)

        for child in getItem("Lights_SF").getAllMembers():
            if child.getState() not in states and child.getName() not in ["Light_SF_Bathroom_Mirror", "Light_SF_Bedroom_Right"]:
                sendCommand(child, OFF)

        sendCommand("Scene6", ON)
        postUpdate("Scene3", OFF)


@rule("scenes_common.py")
class Scene4Rule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("Scene4","ON"),
            ItemCommandTrigger("Light_SF_Bedroom_Left_Long_Pressed", "ON"),
            ItemCommandTrigger("Light_SF_Bedroom_Right_Long_Pressed", "ON")
        ]

    def execute(self, module, input):
        sendCommand("Lights_Indoor", OFF)

        if getItemState("Motiondetector_Outdoor_Switch") == OFF:
            sendCommand("Motiondetector_Outdoor_Switch", ON)

        postUpdate("Scene4", OFF)


@rule("scenes_common.py")
class Scene5Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Scene5","ON")]

    def execute(self, module, input):
        sendCommand("Motiondetector_Outdoor_Carport_Switch", OFF)
        sendCommand("Motiondetector_Outdoor_Frontdoor_Switch", OFF)
        sendCommand("Motiondetector_Outdoor_Terrace_Switch", OFF)
        sendCommand("Motiondetector_Outdoor_Garage_Streetside_Switch", OFF)
        sendCommand("Motiondetector_Outdoor_Garage_Gardenside_Switch", ON)

        postUpdate("Scene5", OFF)


@rule("scenes_common.py")
class Scene6Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Scene6","ON")]

    def execute(self, module, input):
        if getItemState("TV_Online") == ON:
            if input["command"] == OFF:
                sendCommand("TV_Online", OFF)
        else:
            if input["command"] == ON:
                sendCommand("TV_Online", ON)

        postUpdate("Scene6", OFF)
