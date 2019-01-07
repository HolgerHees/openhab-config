from marvin.helper import rule, getItemState, sendCommand, postUpdate, postUpdateIfChanged, getNow, createTimer
from core.triggers import ItemCommandTrigger, ItemStateChangeTrigger
from org.eclipse.smarthome.core.types import UnDefType

lastUpdate = {}
ruleTimeouts = {}

@rule("lights_indoor_livingroom_control.py")
class CeilingRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Lights_FF_Livingroom_Ceiling")]

    def execute(self, module, input):
        global ruleTimeouts
        now = getNow().getMillis()
        last = ruleTimeouts.get("Ceiling_Main",0)
        
        if now - last > 1000:
            ruleTimeouts["Ceiling_Backward"] = now
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
        global ruleTimeouts
        now = getNow().getMillis()
        last = ruleTimeouts.get("Ceiling_Backward",0)
        
        if now - last > 1000:
            value = 0
        
            # check for UnDefType. Happens if I increase or decrease dimming value manually
            if type(getItemState("Light_FF_Livingroom_Diningtable")) is not UnDefType and getItemState("Light_FF_Livingroom_Diningtable").intValue() > value:
                value = getItemState("Light_FF_Livingroom_Diningtable").intValue()
            # check for UnDefType. Happens if I increase or decrease dimming value manually
            if type(getItemState("Light_FF_Livingroom_Couch")) is not UnDefType and getItemState("Light_FF_Livingroom_Couch").intValue() > value:
                value = getItemState("Light_FF_Livingroom_Couch").intValue()

            ruleTimeouts["Ceiling_Main"] = now
            postUpdateIfChanged("Lights_FF_Livingroom_Ceiling", value)


@rule("lights_indoor_livingroom_control.py")
class HueBrightnessRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Light_FF_Livingroom_Hue_Brightness")]

    def execute(self, module, input):
        global ruleTimeouts
        now = getNow().getMillis()
        last = ruleTimeouts.get("Livingroom_Hue_Brightness_Main",0)
        
        if now - last > 1000:
            ruleTimeouts["Livingroom_Hue_Brightness_Backward"] = now
            
            sendCommand("Light_FF_Livingroom_Hue_Brightness1", input["command"])
            sendCommand("Light_FF_Livingroom_Hue_Brightness2", input["command"])
            sendCommand("Light_FF_Livingroom_Hue_Brightness3", input["command"])
            sendCommand("Light_FF_Livingroom_Hue_Brightness4", input["command"])
            sendCommand("Light_FF_Livingroom_Hue_Brightness5", input["command"])
            
            sendCommand("State_Lightprogram", 0)


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
        global ruleTimeouts
        now = getNow().getMillis()
        last = ruleTimeouts.get("Livingroom_Hue_Brightness_Backward",0)
        
        if now - last > 1000:
            ruleTimeouts["Livingroom_Hue_Brightness_Main"] = now
            
            itemName = input['event'].getItemName()
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
            
            sendCommand("State_Lightprogram", 0)


@rule("lights_indoor_livingroom_control.py")
class HueColorRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Light_FF_Livingroom_Hue_Color")]

    def execute(self, module, input):
        global ruleTimeouts
        now = getNow().getMillis()
        last = ruleTimeouts.get("Livingroom_Hue_Color_Main",0)
        
        if now - last > 1000:
            ruleTimeouts["Livingroom_Hue_Color_Backward"] = now

            sendCommand("Light_FF_Livingroom_Hue_Color1", input["command"])
            sendCommand("Light_FF_Livingroom_Hue_Color2", input["command"])
            sendCommand("Light_FF_Livingroom_Hue_Color3", input["command"])
            sendCommand("Light_FF_Livingroom_Hue_Color4", input["command"])
            sendCommand("Light_FF_Livingroom_Hue_Color5", input["command"])
            
            sendCommand("State_Lightprogram", 0)


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
        global ruleTimeouts
        now = getNow().getMillis()
        last = ruleTimeouts.get("Livingroom_Hue_Color_Backward",0)
        
        if now - last > 1000:
            ruleTimeouts["Livingroom_Hue_Color_Main"] = now
            
            itemName = input['event'].getItemName()
            itemCommand = input['event'].getItemCommand()
            
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
                
            sendCommand("State_Lightprogram", 0)

@rule("lights_indoor_livingroom_control.py")
class HueColorProgramRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Lightprogram")]
        self.orgColors = None
        self.timer = None
        
        self.timeout = 30        
        
        self.fadingSteps = 20.0
        
    def _fixColor(self,color):
        if color < 0:
            return 0
        elif color > 255:
            return 255
        return int( color )
    
    def _getCurrentColors(self):
        color1 = getItemState("Light_FF_Livingroom_Hue_Color1").toString().split(",")
        color2 = getItemState("Light_FF_Livingroom_Hue_Color2").toString().split(",")
        color3 = getItemState("Light_FF_Livingroom_Hue_Color3").toString().split(",")
        color4 = getItemState("Light_FF_Livingroom_Hue_Color4").toString().split(",")
        color5 = getItemState("Light_FF_Livingroom_Hue_Color5").toString().split(",")
        return [color1,color2,color3,color4,color5]
    
    def _setCurrentColors(self,data):
        global ruleTimeouts
        ruleTimeouts["Livingroom_Hue_Color_Backward"] = getNow().getMillis()
        
        sendCommand("Light_FF_Livingroom_Hue_Color1",u"{},{},{}".format(data[0][0],data[0][1],data[0][2]))
        sendCommand("Light_FF_Livingroom_Hue_Color2",u"{},{},{}".format(data[1][0],data[1][1],data[1][2]))
        sendCommand("Light_FF_Livingroom_Hue_Color3",u"{},{},{}".format(data[2][0],data[2][1],data[2][2]))
        sendCommand("Light_FF_Livingroom_Hue_Color4",u"{},{},{}".format(data[3][0],data[3][1],data[3][2]))
        sendCommand("Light_FF_Livingroom_Hue_Color5",u"{},{},{}".format(data[4][0],data[4][1],data[4][2]))

    def _fade(self,step,fromColor,toColor,currentColor):
        start = float(fromColor[0])
        diff = ( float(toColor[0]) - start ) / self.fadingSteps
        red = self._fixColor( start + ( diff * step ) )

        start = float(fromColor[1])
        diff = ( float(toColor[1]) - start ) / self.fadingSteps
        green = self._fixColor( start + ( diff * step ) )

        start = float(fromColor[2])
        diff = ( float(toColor[2]) - start ) / self.fadingSteps
        blue = self._fixColor( start + ( diff * step ) )

        return [u"{}".format(red),u"{}".format(green),u"{}".format(blue)]
    
    def callbackFaded(self,step,data):
        if getItemState("State_Lightprogram").intValue() == 0:
            return
            
        color1, color2, color3, color4, color5 = data
        
        if step == self.fadingSteps:
            newColor1 = color2
            newColor2 = color3
            newColor3 = color4
            newColor4 = color5
            newColor5 = color1
        else:
            currentColor1, currentColor2, currentColor3, currentColor4 , currentColor5 = self._getCurrentColors()
            
            newColor1 = self._fade( step, color1, color2, currentColor1 )
            newColor2 = self._fade( step, color2, color3, currentColor2 )
            newColor3 = self._fade( step, color3, color4, currentColor3 )
            newColor4 = self._fade( step, color4, color5, currentColor4 )
            newColor5 = self._fade( step, color5, color1, currentColor5 )
            
        self.log.info(u"{} - 1 {}, from {} => {}".format(step,newColor1,color1, color2))
        self.log.info(u"{} - 2 {}, from {} => {}".format(step,newColor2,color2, color3))
        self.log.info(u"{} - 3 {}, from {} => {}".format(step,newColor3,color3, color4))
        self.log.info(u"{} - 4 {}, from {} => {}".format(step,newColor4,color4, color5))
        self.log.info(u"{} - 5 {}, from {} => {}".format(step,newColor5,color5, color1))
        
        self._setCurrentColors([newColor1,newColor2,newColor3,newColor4,newColor5])
        
        if step < self.fadingSteps:
            self.timer = createTimer(self.timeout, self.callbackFaded, [step + 1, data] )
            self.timer.start()
        else:
            self.timer = createTimer(self.timeout, self.callbackFaded, [1, self._getCurrentColors() ] )
            self.timer.start()
    
    def callback(self):
        if getItemState("State_Lightprogram").intValue() == 0:
            return
        
        color1 = getItemState("Light_FF_Livingroom_Hue_Color1")
        color2 = getItemState("Light_FF_Livingroom_Hue_Color2")
        color3 = getItemState("Light_FF_Livingroom_Hue_Color3")
        color4 = getItemState("Light_FF_Livingroom_Hue_Color4")
        color5 = getItemState("Light_FF_Livingroom_Hue_Color5")
            
        global ruleTimeouts
        ruleTimeouts["Livingroom_Hue_Color_Backward"] = getNow().getMillis()
    
        sendCommand("Light_FF_Livingroom_Hue_Color1",color2)
        sendCommand("Light_FF_Livingroom_Hue_Color2",color3)
        sendCommand("Light_FF_Livingroom_Hue_Color3",color4)
        sendCommand("Light_FF_Livingroom_Hue_Color4",color5)
        sendCommand("Light_FF_Livingroom_Hue_Color5",color1)
                    
        self.timer = createTimer(self.timeout, self.callback )
        self.timer.start()
            
    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
            
            if self.orgColors != None:
                self._setCurrentColors(self.orgColors)
                self.orgColors = None
        
        itemState = input["event"].getItemState().intValue()
        
        if itemState > 0:
            self.orgColors = self._getCurrentColors()

            if itemState == 1:

                self.timer = createTimer(1, self.callback)
                self.timer.start()

            elif itemState == 2:
        
                self.timer = createTimer(1, self.callbackFaded, [1, self.orgColors])
                self.timer.start()'''
