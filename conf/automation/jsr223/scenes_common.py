from shared.helper import rule, getItem, getItemState, sendCommand, postUpdate, postUpdateIfChanged
from shared.triggers import ItemCommandTrigger


#@rule()
## watch tv
#class ScenesCommon_pOther_Scene1:
#    def __init__(self):
#        self.triggers = [ItemCommandTrigger("pOther_Scene1",command="ON")]

#    def execute(self, module, input):
#        sendCommand("gGF_Livingroom_Light_Hue_Color", 60)

#        states = [OFF, PercentType.ZERO]

#        for child in getItem("gGF_Lights").getAllMembers():
#            if child.getState() not in states and child.getName() != "gGF_Livingroom_Light_Hue_Color":
#                sendCommand(child, OFF)

#        for child in getItem("gFF_Lights").getAllMembers():
#            if child.getState() not in states:
#                sendCommand(child, OFF)

#        postUpdate("pOther_Scene1", OFF)


#@rule()
## wakeup
#class ScenesCommon_pOther_Scene2:
#    def __init__(self):
#        self.triggers = [ItemCommandTrigger("pOther_Scene2",command="ON")]

#    def execute(self, module, input):
#        sendCommand("pGF_Corridor_Light_Ceiling_Powered", ON)
#        sendCommand("pFF_Bathroom_Light_Ceiling_Powered", ON)
#        sendCommand("pFF_Bathroom_Light_Mirror_Powered", ON)
#        sendCommand("pFF_Bedroom_Light_Ceiling_Powered", ON)

#        postUpdate("pOther_Scene2", OFF)


#@rule()
## go to bed
#class ScenesCommon_pOther_Scene3:
#    def __init__(self):
#        self.triggers = [ItemCommandTrigger("pOther_Scene3",command="ON")]

#    def execute(self, module, input):
#        sendCommand("pGF_Corridor_Light_Hue_Color", 60)
#        sendCommand("pFF_Bathroom_Light_Ceiling_Powered", ON)
#        sendCommand("pFF_Bathroom_Light_Mirror_Powered", ON)
#        sendCommand("pFF_Bedroom_Light_Hue_Right_Switch", ON)

#        states = [OFF, PercentType.ZERO]

#        for child in getItem("gGF_Lights").getAllMembers():
#            if child.getState() not in states and child.getName() != "pGF_Corridor_Light_Hue_Color":
#                sendCommand(child, OFF)

#        #for child in getItem("gFF_Lights").getAllMembers():
#        #    if child.getState() not in states and child.getName() not in ["pFF_Bathroom_Light_Mirror_Powered", "pFF_Bedroom_Light_Hue_Right_Switch"]:
#        #        sendCommand(child, OFF)

#        sendCommand("pOther_Scene6", ON)
#        postUpdate("pOther_Scene3", OFF)


# pOther_Scene4 => is handled in presence_detection.py


@rule()
# go outside
class ScenesCommon_pOther_Scene5:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pOther_Scene5",command="ON")]
        #postUpdateIfChanged("pOther_Scene5", OFF)

    def execute(self, module, input):
        sendCommand("pOutdoor_Carport_Automatic_Switch", OFF)
        sendCommand("pOutdoor_Streedside_Frontdoor_Automatic_Switch", OFF)
        sendCommand("pOutdoor_Terrace_Automatic_Switch", OFF)
        sendCommand("pOutdoor_Streedside_Garage_Automatic_Switch", OFF)
        sendCommand("pOutdoor_Garden_Garage_Automatic_Switch", ON)
        sendCommand("pOutdoor_Toolshed_Right_Automatic_Switch", OFF)

        #postUpdate("pOther_Scene5", OFF)

#@rule()
#class ScenesCommon_pOther_Scene6:
#    def __init__(self):
#        self.triggers = [ItemCommandTrigger("pOther_Scene6",command="ON")]

#    def execute(self, module, input):
#        if getItemState("TV_Online") == ON:
#            if input["command"] == OFF:
#                sendCommand("TV_Online", OFF)
#        else:
#            if input["command"] == ON:
#                sendCommand("TV_Online", ON)

#        postUpdate("pOther_Scene6", OFF)
