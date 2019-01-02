from marvin.helper import rule, getItemState, sendCommand, postUpdateIfChanged, getNow, createTimer
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

@rule("lights_indoor_livingroom_control.py")
class HueColorProgramRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Lightprogram")]
        self.timer = None
        self.steps = 6

    def fade(self,step,fromColor,toColor,currentColor):
        
        diff = ( int(toColor[0]) - int(fromColor[0]) ) / self.steps
        red = int(currentColor[0]) + diff

        diff = ( int(toColor[1]) - int(fromColor[1]) ) / self.steps
        green = int(currentColor[1]) + diff

        diff = ( int(toColor[2]) - int(fromColor[2]) ) / self.steps
        blue = int(currentColor[2]) + diff

        return [u"{}".format(red),u"{}".format(green),u"{}".format(blue)]
    
    def callbackFaded(self,step,data):
        if getItemState("State_Lightprogram").intValue() > 0 and getItemState("Light_FF_Livingroom_Hue_Brightness").intValue() > 0:
            
            if step == 1:
                fromColor1 = getItemState("Light_FF_Livingroom_Hue_Color1").toString().split(",")
                fromColor2 = getItemState("Light_FF_Livingroom_Hue_Color2").toString().split(",")
                fromColor3 = getItemState("Light_FF_Livingroom_Hue_Color3").toString().split(",")
                fromColor4 = getItemState("Light_FF_Livingroom_Hue_Color4").toString().split(",")
                fromColor5 = getItemState("Light_FF_Livingroom_Hue_Color5").toString().split(",")
                data = [fromColor1,fromColor2,fromColor3,fromColor4,fromColor5]

            color1 = data[0]
            color2 = data[1]
            color3 = data[2]
            color4 = data[3]
            color5 = data[4]
            
            currentColor1 = getItemState("Light_FF_Livingroom_Hue_Color1").toString().split(",")
            currentColor2 = getItemState("Light_FF_Livingroom_Hue_Color2").toString().split(",")
            currentColor3 = getItemState("Light_FF_Livingroom_Hue_Color3").toString().split(",")
            currentColor4 = getItemState("Light_FF_Livingroom_Hue_Color4").toString().split(",")
            currentColor5 = getItemState("Light_FF_Livingroom_Hue_Color5").toString().split(",")
            
            if step == self.steps:
                newColor1 = color2
                newColor2 = color3
                newColor3 = color4
                newColor4 = color5
                newColor5 = color1
            else:
                newColor1 = self.fade( step, color1, color2, currentColor1 )
                newColor2 = self.fade( step, color2, color3, currentColor2 )
                newColor3 = self.fade( step, color3, color4, currentColor3 )
                newColor4 = self.fade( step, color4, color5, currentColor4 )
                newColor5 = self.fade( step, color5, color1, currentColor5 )
                
            #self.log.info(u"{} {} {}".format(color1,color2,newColor1))

            sendCommand("Light_FF_Livingroom_Hue_Color1",u"{},{},{}".format(newColor1[0],newColor1[1],newColor1[2]))
            sendCommand("Light_FF_Livingroom_Hue_Color2",u"{},{},{}".format(newColor2[0],newColor2[1],newColor2[2]))
            sendCommand("Light_FF_Livingroom_Hue_Color3",u"{},{},{}".format(newColor3[0],newColor3[1],newColor3[2]))
            sendCommand("Light_FF_Livingroom_Hue_Color4",u"{},{},{}".format(newColor4[0],newColor4[1],newColor4[2]))
            sendCommand("Light_FF_Livingroom_Hue_Color5",u"{},{},{}".format(newColor5[0],newColor5[1],newColor5[2]))
            
            if step < self.steps:
                timer = createTimer(2, self.callbackFaded, [step + 1, data] )
                timer.start()
            else:
                self.timer = createTimer(30, self.callbackFaded, [1,[]] )
                self.timer.start()
    
    def callback(self):
        if getItemState("State_Lightprogram").intValue() > 0 and getItemState("Light_FF_Livingroom_Hue_Brightness").intValue() > 0:
            color1 = getItemState("Light_FF_Livingroom_Hue_Color1")
            color2 = getItemState("Light_FF_Livingroom_Hue_Color2")
            color3 = getItemState("Light_FF_Livingroom_Hue_Color3")
            color4 = getItemState("Light_FF_Livingroom_Hue_Color4")
            color5 = getItemState("Light_FF_Livingroom_Hue_Color5")
                
            sendCommand("Light_FF_Livingroom_Hue_Color1",color2)
            sendCommand("Light_FF_Livingroom_Hue_Color2",color3)
            sendCommand("Light_FF_Livingroom_Hue_Color3",color4)
            sendCommand("Light_FF_Livingroom_Hue_Color4",color5)
            sendCommand("Light_FF_Livingroom_Hue_Color5",color1)
            
            self.timer = createTimer(30, self.callback )
            self.timer.start()
            
    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
        
        if input["event"].getItemState().intValue() > 0:

            self.timer = createTimer(1, self.callback)
            self.timer.start()
