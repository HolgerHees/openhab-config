from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger, ItemCommandTrigger

from datetime import datetime


rule_timeouts = {}

@rule(
    triggers = [
        ItemCommandTrigger("gGF_Livingroom_Light_Hue_Color")
    ]
)
class HueColorMain:
    def execute(self, module, input):
        global rule_timeouts
        rule_timeouts["Livingroom_Hue_Color_Backward"] = datetime.now().astimezone()

        #command = input['event'].getItemCommand()
        
        #colors = command.toString().split(",")

        #red = round(float(colors[0]))
        #green = round(float(colors[1]))
        #blue = round(float(colors[1]))
        
        #command = "{},{},{}".format(red,green,blue)+

        #Registry.getItem("pGF_Livingroom_Light_Hue1_Color").sendCommand(command)
        #Registry.getItem("pGF_Livingroom_Light_Hue2_Color").sendCommand(command)
        #Registry.getItem("pGF_Livingroom_Light_Hue4_Color").sendCommand(command)
        #Registry.getItem("pGF_Livingroom_Light_Hue5_Color").sendCommand(command)
        
        Registry.getItem("pGF_Livingroom_Light_Hue_Scene").postUpdate("")

@rule(
    triggers = [
        ItemCommandTrigger("pGF_Livingroom_Light_Hue1_Color"),
        ItemCommandTrigger("pGF_Livingroom_Light_Hue2_Color"),
        ItemCommandTrigger("pGF_Livingroom_Light_Hue4_Color"),
        ItemCommandTrigger("pGF_Livingroom_Light_Hue5_Color")
    ]
)
class HueColorIndividual:
    def execute(self, module, input):
        global rule_timeouts
        now = datetime.now().astimezone()
        last = rule_timeouts.get("Livingroom_Hue_Color_Backward",now)
        
        if (now - last).total_seconds() > 1:
            Registry.getItem("pGF_Livingroom_Light_Hue_Scene").postUpdate("")

