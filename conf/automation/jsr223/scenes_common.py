from shared.helper import rule, getItem, getItemState, sendCommand, postUpdate
from core.triggers import ItemCommandTrigger


@rule("scenes_common.py")
# watch tv
class pOther_Scene1Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene1",command="ON")]

    def execute(self, module, input):
        sendCommand("gGF_Livingroom_Light_Hue_Brightness", 60)

        states = [OFF, PercentType.ZERO]

        for child in getItem("gGF_Lights").getAllMembers():
            if child.getState() not in states and child.getName() != "gGF_Livingroom_Light_Hue_Brightness":
                sendCommand(child, OFF)

        for child in getItem("gFF_Lights").getAllMembers():
            if child.getState() not in states:
                sendCommand(child, OFF)

        postUpdate("pOther_Scene1", OFF)


@rule("scenes_common.py")
# wakeup
class pOther_Scene2Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene2",command="ON")]

    def execute(self, module, input):
        sendCommand("pGF_Corridor_Light_Ceiling_Powered", ON)
        sendCommand("pFF_Bathroom_Light_Ceiling_Powered", ON)
        sendCommand("pFF_Bathroom_Light_Mirror_Powered", ON)
        sendCommand("pFF_Bedroom_Light_Ceiling_Powered", ON)

        postUpdate("pOther_Scene2", OFF)


@rule("scenes_common.py")
# go to bed
class pOther_Scene3Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene3",command="ON")]

    def execute(self, module, input):
        sendCommand("pGF_Corridor_Light_Hue_Brightness", 60)
        sendCommand("pFF_Bathroom_Light_Ceiling_Powered", ON)
        sendCommand("pFF_Bathroom_Light_Mirror_Powered", ON)
        sendCommand("pFF_Bedroom_Light_Hue_Right_Switch", ON)

        states = [OFF, PercentType.ZERO]

        for child in getItem("gGF_Lights").getAllMembers():
            if child.getState() not in states and child.getName() != "pGF_Corridor_Light_Hue_Brightness":
                sendCommand(child, OFF)

        #for child in getItem("gFF_Lights").getAllMembers():
        #    if child.getState() not in states and child.getName() not in ["pFF_Bathroom_Light_Mirror_Powered", "pFF_Bedroom_Light_Hue_Right_Switch"]:
        #        sendCommand(child, OFF)

        sendCommand("pOther_Scene6", ON)
        postUpdate("pOther_Scene3", OFF)


# pOther_Scene4 => is handled in presence_detection.py


@rule("scenes_common.py")
class pOther_Scene5Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene5",command="ON")]

    def execute(self, module, input):
        sendCommand("pOutdoor_Carport_Automatic_Switch", OFF)
        sendCommand("pOutdoor_Streedside_Frontdoor_Automatic_Switch", OFF)
        sendCommand("pOutdoor_Garden_Terrace_Automatic_Switch", OFF)
        sendCommand("pOutdoor_Streedside_Garage_Automatic_Switch", OFF)
        sendCommand("pOutdoor_Garden_Garage_Automatic_Switch", ON)

        postUpdate("pOther_Scene5", OFF)


@rule("scenes_common.py")
class pOther_Scene6Rule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene6",command="ON")]

    def execute(self, module, input):
        if getItemState("TV_Online") == ON:
            if input["command"] == OFF:
                sendCommand("TV_Online", OFF)
        else:
            if input["command"] == ON:
                sendCommand("TV_Online", ON)

        postUpdate("pOther_Scene6", OFF)


# pOther_Scene7, pOther_Scene8 & pOther_Scene9 => is handled in tablet.py
