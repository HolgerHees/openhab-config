from shared.helper import rule, getItemState, postUpdate, sendCommand, sendCommandIfChanged, itemLastChangeNewerThen, getGroupMemberChangeTrigger, startTimer
from core.triggers import ItemStateChangeTrigger
from java.time import ZonedDateTime

configs = [
    { "contact": "pGF_Livingroom_Openingcontact_Window_Terrace_State", "shutter": "pGF_Livingroom_Shutter_Terrace_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Livingroom", "sunprotectionOnlyIfAway": True },
    { "contact": "pGF_Livingroom_Openingcontact_Window_Couch_State", "shutter": "pGF_Livingroom_Shutter_Couch_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Livingroom", "sunprotectionOnlyIfAway": True },
    { "contact": "pGF_Kitchen_Openingcontact_Window_State", "shutter": "pGF_Kitchen_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Livingroom", "sunprotectionOnlyIfAway": True },
    { "contact": "pGF_Guestroom_Openingcontact_Window_State", "shutter": "pGF_Guestroom_Shutter_Control" },
    { "contact": "pGF_Guesttoilet_Openingcontact_Window_State", "shutter": "pGF_Guesttoilet_Shutter_Control" },
    { "contact": "pFF_Bedroom_Openingcontact_Window_State", "shutter": "pFF_Bedroom_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Bedroom" },
    { "contact": "pFF_Dressingroom_Openingcontact_Window_State", "shutter": "pFF_Dressingroom_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Dressingroom" },
    { "contact": "pFF_Child1_Openingcontact_Window_State", "shutter": "pFF_Child1_Shutter_Control" },
    { "contact": "pFF_Child2_Openingcontact_Window_State", "shutter": "pFF_Child2_Shutter_Control" },
    { "contact": "pFF_Bathroom_Openingcontact_Window_State", "shutter": "pFF_Bathroom_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Bathroom" },
    { "contact": "pFF_Attic_Openingcontact_Window_State", "shutter": "pFF_Attic_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Attic" },
]

contact_map = {}
shutter_map = {}
sunprotection_map = {}
for config in configs:
    contact_map[config["contact"]] = config
    shutter_map[config["shutter"]] = config
    
    if "sunprotection" not in config:
        continue
      
    if config["sunprotection"] not in sunprotection_map:
        sunprotection_map[config["sunprotection"]] = []
  
    sunprotection_map[config["sunprotection"]].append(config)

@rule("rollershutter_auto.py")
class RollershutterAutoCleanupRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Manual_State_Auto_Rollershutter", state="OFF")]

    def execute(self, module, input):
        postUpdate("pOther_Manual_State_Auto_Sunprotection", OFF)

@rule("rollershutter_auto.py")
class RollershutterAutoMorningEveningRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Automatic_State_Rollershutter")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Rollershutter") != ON:
            return
      
        if getItemState("pOther_Automatic_State_Rollershutter") == ON:
            for config in configs:
                if getItemState(config["contact"]) != CLOSED: 
                    continue
                sendCommand(config["shutter"], DOWN)
        elif getItemState("pOther_Presence_State").intValue() == 0:
            sendCommand("gShutters", UP)

@rule("rollershutter_auto.py")
class RollershutterAutoWindowContactRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gFF_Sensor_Window")
        
    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Rollershutter") != ON:
            return
          
        contactItemName = input['event'].getItemName()
        config = contact_map[contactItemName]

        state = None
        if input['event'].getItemState() == OPEN:
            state = UP
        else:
            if getItemState("pOther_Automatic_State_Rollershutter") == ON:
                state = DOWN
            elif ("sunprotection" in config and getItemState(config["sunprotection"]) == ON and "sunprotectionOnlyIfAway" not in config):
                state = DOWN
            
        if state is None:
            return
        
        sendCommand(config["shutter"], state)

@rule("rollershutter_auto.py")
class RollershutterAutoPresenceRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State")]
        self.presenceTimer = None

    def updateCallback(self,state):
        for config in configs:
            # handle only shutters which depends on presence state
            if "sunprotectionOnlyIfAway" not in config:
                continue

            if state == DOWN:
                if getItemState(config["contact"]) != CLOSED:
                    continue

                if getItemState(config["sunprotection"]) != ON:
                    continue

            sendCommandIfChanged(config["shutter"],state)

        self.presenceTimer = None

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Rollershutter") != ON:
            return
          
        if self.presenceTimer != None:
            self.presenceTimer.cancel()
            self.presenceTimer = None
    
        if input['event'].getOldItemState().intValue() == 0:
            self.updateCallback(UP)
        elif input['event'].getItemState().intValue() == 0:
            self.presenceTimer = startTimer(self.log, 1800, self.updateCallback, args = [ DOWN ])

@rule("rollershutter_auto.py")
class RollershutterAutoSunprotectionRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Attic"),
            ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Bathroom"),
            ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Dressingroom"),
            ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Livingroom")
        ]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Rollershutter") != ON:
            return
          
        sunprotectionItemName = input['event'].getItemName()
        configs = sunprotection_map[sunprotectionItemName]
        state = DOWN if input['event'].getItemState() == ON else UP
        
        for config in configs:
            if state == DOWN:
                # shutdown shutters only if the window is closed
                if getItemState(config["contact"]) != CLOSED:
                    continue
                
                # skip closing shutters if we must be away but we are still present or not long enough away
                if "sunprotectionOnlyIfAway" in config and (getItemState("pOther_Presence_State").intValue() != 0 or itemLastChangeNewerThen("pOther_Presence_State", ZonedDateTime.now().minusSeconds(1800))):
                    continue
          
            sendCommand(config["shutter"], state)

          
@rule("rollershutter_auto.py")
class TerraceAutoSunprotectionRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Terrace")
        ]

    def execute(self, module, input):
        if getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == 1:
            pass
        elif getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == 2:
            # DOWN only if automatic is enabled and (people are present or where present quite recently or terrace door is open)
            if (getItemState("pOther_Manual_State_Auto_Sunprotection") == ON
                  and ( getItemState("pOther_Presence_State").intValue() != 0 or itemLastChangeNewerThen("pOther_Presence_State", ZonedDateTime.now().minusMinutes(120)) or getItemState("pGF_Livingroom_Openingcontact_Window_Terrace_State") == OPEN )
               ):
                #self.log.info(u"down")
                sendCommand("pOutdoor_Terrace_Shading_Left_Control", DOWN)
                sendCommand("pOutdoor_Terrace_Shading_Right_Control", DOWN)
        else:
            #self.log.info(u"up")
            # UP always when sun protection time is over
            sendCommand("pOutdoor_Terrace_Shading_Left_Control", UP)
            sendCommand("pOutdoor_Terrace_Shading_Right_Control", UP)

#sendCommand("pOther_Automatic_State_Sunprotection_Terrace", 0)
