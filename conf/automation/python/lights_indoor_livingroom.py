from openhab import rule, Registry, Timer
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

        command = input['event'].getItemCommand()
        
        #colors = command.toString().split(",")

        #red = round(float(colors[0]))
        #green = round(float(colors[1]))
        #blue = round(float(colors[1]))
        
        #command = "{},{},{}".format(red,green,blue)+

        Registry.getItem("pGF_Livingroom_Light_Hue1_Color").sendCommand(command)
        Registry.getItem("pGF_Livingroom_Light_Hue2_Color").sendCommand(command)
        Registry.getItem("pGF_Livingroom_Light_Hue4_Color").sendCommand(command)
        Registry.getItem("pGF_Livingroom_Light_Hue5_Color").sendCommand(command)
        
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
        
        if (last - now).total_seconds() > 1:
            Registry.getItem("pGF_Livingroom_Light_Hue_Scene").postUpdate("")
            Registry.getItem("pOther_Manual_State_Lightprogram").sendCommand(0)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Manual_State_Lightprogram")
    ]
)
class HueColorProgram:
    def __init__(self):
        self.original_colors = None
        self.timer = None
        
        self.timeout = 30        
        
        self.fading_steps = 20.0
        
    def _fixColor(self,color):
        if color < 0:
            return 0
        elif color > 255:
            return 255
        return int( color )
    
    def _getCurrentColors(self):
        color1 = Registry.getItemState("pGF_Livingroom_Light_Hue1_Color").toString().split(",")
        color2 = Registry.getItemState("pGF_Livingroom_Light_Hue2_Color").toString().split(",")
        color4 = Registry.getItemState("pGF_Livingroom_Light_Hue4_Color").toString().split(",")
        color5 = Registry.getItemState("pGF_Livingroom_Light_Hue5_Color").toString().split(",")
        return [color1,color2,color4,color5]
    
    def _setCurrentColors(self,data):
        global rule_timeouts
        rule_timeouts["Livingroom_Hue_Color_Backward"] = datetime.now().astimezone()
        
        Registry.getItem("pGF_Livingroom_Light_Hue1_Color").sendCommand("{},{},{}".format(data[0][0],data[0][1],data[0][2]))
        Registry.getItem("pGF_Livingroom_Light_Hue2_Color").sendCommand("{},{},{}".format(data[1][0],data[1][1],data[1][2]))
        Registry.getItem("pGF_Livingroom_Light_Hue4_Color").sendCommand("{},{},{}".format(data[3][0],data[3][1],data[3][2]))
        Registry.getItem("pGF_Livingroom_Light_Hue5_Color").sendCommand("{},{},{}".format(data[4][0],data[4][1],data[4][2]))

    def _fade(self,step,from_color,to_color,current_color):
        start = float(from_color[0])
        diff = ( float(to_color[0]) - start ) / self.fading_steps
        red = self._fixColor( start + ( diff * step ) )

        start = float(from_color[1])
        diff = ( float(to_color[1]) - start ) / self.fading_steps
        green = self._fixColor( start + ( diff * step ) )

        start = float(from_color[2])
        diff = ( float(to_color[2]) - start ) / self.fading_steps
        blue = self._fixColor( start + ( diff * step ) )

        return ["{}".format(red),"{}".format(green),"{}".format(blue)]
    
    def callbackFaded(self,step,data):
        if Registry.getItemState("pOther_Manual_State_Lightprogram").intValue() == 0:
            return
            
        color1, color2, color4, color5 = data
        
        if step == self.fading_steps:
            newColor1 = color2
            newColor2 = color4
            newColor4 = color5
            newColor5 = color1
        else:
            current_color1, current_color2, current_color4 , current_color5 = self._getCurrentColors()
            
            newColor1 = self._fade( step, color1, color2, current_color1 )
            newColor2 = self._fade( step, color2, color4, current_color2 )
            newColor4 = self._fade( step, color4, color5, current_color4 )
            newColor5 = self._fade( step, color5, color1, current_color5 )
            
        self.logger.info("{} - 1 {}, from {} => {}".format(step,newColor1,color1, color2))
        self.logger.info("{} - 2 {}, from {} => {}".format(step,newColor2,color2, color4))
        self.logger.info("{} - 4 {}, from {} => {}".format(step,newColor4,color4, color5))
        self.logger.info("{} - 5 {}, from {} => {}".format(step,newColor5,color5, color1))
        
        self._setCurrentColors([newColor1,newColor2,newColor4,newColor5])
        
        if step < self.fading_steps:
            self.timer = Timer.createTimeout(self.timeout, self.callbackFaded, [step + 1, data] )
        else:
            self.timer = Timer.createTimeout(self.timeout, self.callbackFaded, [1, self._getCurrentColors() ] )
    
    def callback(self):
        if Registry.getItemState("pOther_Manual_State_Lightprogram").intValue() == 0:
            return
        
        color1 = Registry.getItemState("pGF_Livingroom_Light_Hue1_Color")
        color2 = Registry.getItemState("pGF_Livingroom_Light_Hue2_Color")
        color4 = Registry.getItemState("pGF_Livingroom_Light_Hue4_Color")
        color5 = Registry.getItemState("pGF_Livingroom_Light_Hue5_Color")
            
        global rule_timeouts
        rule_timeouts["Livingroom_Hue_Color_Backward"] = datetime.now().astimezone()
    
        Registry.getItem("pGF_Livingroom_Light_Hue1_Color").sendCommand(color2)
        Registry.getItem("pGF_Livingroom_Light_Hue2_Color").sendCommand(color4)
        Registry.getItem("pGF_Livingroom_Light_Hue4_Color").sendCommand(color5)
        Registry.getItem("pGF_Livingroom_Light_Hue5_Color").sendCommand(color1)
                    
        self.timer = Timer.createTimeout(self.timeout, self.callback )
            
    def execute(self, module, input):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
            
            if self.original_colors != None:
                self._setCurrentColors(self.original_colors)
                self.original_colors = None
        
        item_state = input["event"].getItemState().intValue()
        
        if item_state > 0:
            self.original_colors = self._getCurrentColors()

            if item_state == 1:

                self.timer = Timer.createTimeout(1, self.callback)

            elif item_state == 2:
        
                self.timer = Timer.createTimeout(1, self.callbackFaded, [1, self.original_colors])
