from marvin.helper import rule, getItemState, sendCommand, postUpdateIfChanged, getNow
from core.triggers import ItemCommandTrigger, ItemStateChangeTrigger
from org.eclipse.smarthome.core.types import UnDefType

lastUpdate = {}

@rule("lights_indoor_livingroom_control.py")
class CeilingRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Lights_FF_Livingroom_Ceiling")]

    def execute(self, module, input):
        global lastUpdate
        now = getNow().getMillis()
            
        sendCommand("Light_FF_Livingroom_Diningtable", input["command"])
        lastUpdate["Light_FF_Livingroom_Diningtable"] = now
        
        sendCommand("Light_FF_Livingroom_Couch", input["command"])
        lastUpdate["Light_FF_Livingroom_Couch"] = now


@rule("lights_indoor_livingroom_control.py")
class CeilingBackwardRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Light_FF_Livingroom_Diningtable"),
            ItemStateChangeTrigger("Light_FF_Livingroom_Couch")
        ]

    def execute(self, module, input):
        global lastUpdate
        last = lastUpdate.get(input['event'].getItemName(),0)
        
        if getNow().getMillis() - last > 1000:
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
        global lastUpdate
        now = getNow().getMillis()
        
        sendCommand("Light_FF_Livingroom_Hue_Brightness1", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Brightness1"] = now
        
        sendCommand("Light_FF_Livingroom_Hue_Brightness2", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Brightness2"] = now
        
        sendCommand("Light_FF_Livingroom_Hue_Brightness3", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Brightness3"] = now
        
        sendCommand("Light_FF_Livingroom_Hue_Brightness4", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Brightness4"] = now
        
        sendCommand("Light_FF_Livingroom_Hue_Brightness5", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Brightness5"] = now


@rule("lights_indoor_livingroom_control.py")
class HueBrightnessBackwardRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Brightness1"),
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Brightness2"),
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Brightness3"),
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Brightness4"),
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Brightness5")
        ]

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        
        global lastUpdate
        last = lastUpdate.get(itemName,0)

        if getNow().getMillis() - last > 1000:
            itemCommand = input['event'].getItemCommand()
            
            hue1 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Brightness1" else getItemState("Light_FF_Livingroom_Hue_Brightness1")
            hue2 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Brightness2" else getItemState("Light_FF_Livingroom_Hue_Brightness2")
            hue3 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Brightness3" else getItemState("Light_FF_Livingroom_Hue_Brightness3")
            hue4 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Brightness4" else getItemState("Light_FF_Livingroom_Hue_Brightness4")
            hue5 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Brightness5" else getItemState("Light_FF_Livingroom_Hue_Brightness5")
            
            value = 0
            if hue1 > value:
                value = hue1
            if hue2 > value:
                value = hue2
            if hue3 > value:
                value = hue3
            if hue4 > value:
                value = hue4
            if hue5 > value:
                value = hue5

            postUpdateIfChanged("Light_FF_Livingroom_Hue_Brightness", value)


@rule("lights_indoor_livingroom_control.py")
class HueColorRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Light_FF_Livingroom_Hue_Color")]

    def execute(self, module, input):
        global lastUpdate
        now = getNow().getMillis()
        
        sendCommand("Light_FF_Livingroom_Hue_Color1", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Color1"] = now
        
        sendCommand("Light_FF_Livingroom_Hue_Color2", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Color2"] = now
        
        sendCommand("Light_FF_Livingroom_Hue_Color3", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Color3"] = now
        
        sendCommand("Light_FF_Livingroom_Hue_Color4", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Color4"] = now
        
        sendCommand("Light_FF_Livingroom_Hue_Color5", input["command"])
        lastUpdate["Light_FF_Livingroom_Hue_Color5"] = now


@rule("lights_indoor_livingroom_control.py")
class HueColorBackwardRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Color1"),
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Color2"),
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Color3"),
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Color4"),
            ItemCommandTrigger("Light_FF_Livingroom_Hue_Color5")
        ]

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        
        global lastUpdate
        last = lastUpdate.get(itemName,0)

        if getNow().getMillis() - last > 1000:
            itemCommand = input['event'].getItemCommand()
            
            #self.log.info(u"{}".format(itemCommand))
            
            color1 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Color1" else getItemState("Light_FF_Livingroom_Hue_Color1")
            color2 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Color2" else getItemState("Light_FF_Livingroom_Hue_Color2")
            color3 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Color3" else getItemState("Light_FF_Livingroom_Hue_Color3")
            color4 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Color4" else getItemState("Light_FF_Livingroom_Hue_Color4")
            color5 = itemCommand if itemName == "Light_FF_Livingroom_Hue_Color5" else getItemState("Light_FF_Livingroom_Hue_Color5")

            if color1 == itemCommand \
                    and color2 == itemCommand \
                    and color3 == itemCommand \
                    and color4 == itemCommand \
                    and color5 == itemCommand:
                postUpdateIfChanged("Light_FF_Livingroom_Hue_Color", itemCommand)
