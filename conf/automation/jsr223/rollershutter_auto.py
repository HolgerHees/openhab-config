import math
from java.time import ZonedDateTime

from shared.helper import rule, getItemState, sendCommand, sendCommandIfChanged, itemLastChangeNewerThen, getGroupMemberChangeTrigger, startTimer
from shared.triggers import ItemStateChangeTrigger

from custom.presence import PresenceHelper
from custom.sunprotection import SunProtectionHelper
from custom.flags import FlagHelper


configs = [
    { "contact": "pGF_Livingroom_Openingcontact_Window_Terrace_State", "shutter": "pGF_Livingroom_Shutter_Terrace_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Livingroom", "sunprotectionOnlyIfAway": True },
    { "contact": "pGF_Livingroom_Openingcontact_Window_Couch_State", "shutter": "pGF_Livingroom_Shutter_Couch_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Livingroom", "sunprotectionOnlyIfAway": True },
    { "contact": "pGF_Kitchen_Openingcontact_Window_State", "shutter": "pGF_Kitchen_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Livingroom", "sunprotectionOnlyIfAway": True },
    { "contact": "pGF_Workroom_Openingcontact_Window_State", "shutter": "pGF_Workroom_Shutter_Control" },
    { "contact": "pGF_Guesttoilet_Openingcontact_Window_State", "shutter": "pGF_Guesttoilet_Shutter_Control" },
    { "contact": "pFF_Bedroom_Openingcontact_Window_State", "shutter": "pFF_Bedroom_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Bedroom" },
    { "contact": "pFF_Dressingroom_Openingcontact_Window_State", "shutter": "pFF_Dressingroom_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Dressingroom" },
    { "contact": "pFF_Fitnessroom_Openingcontact_Window_State", "shutter": "pFF_Fitnessroom_Shutter_Control" },
    { "contact": "pFF_Makeuproom_Openingcontact_Window_State", "shutter": "pFF_Makeuproom_Shutter_Control" },
    { "contact": "pFF_Bathroom_Openingcontact_Window_State", "shutter": "pFF_Bathroom_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Bathroom" },
    { "contact": "pFF_Attic_Openingcontact_Window_State", "shutter": "pFF_Attic_Shutter_Control", "sunprotection": "pOther_Automatic_State_Sunprotection_Attic" },
]

contact_map = {}
#shutter_map = {}
sunprotection_map = {}
for config in configs:
    contact_map[config["contact"]] = config
    #shutter_map[config["shutter"]] = config
    
    if "sunprotection" not in config:
        continue
      
    if config["sunprotection"] not in sunprotection_map:
        sunprotection_map[config["sunprotection"]] = []
  
    sunprotection_map[config["sunprotection"]].append(config)

@rule()
class RollershutterAutoMorningEvening:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Automatic_State_Rollershutter"),
            ItemStateChangeTrigger("pOther_Presence_State", state=PresenceHelper.STATE_AWAY)
        ]

    def execute(self, module, input):
        if not FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_TIME_DEPENDENT, getItemState("pOther_Manual_State_Auto_Rollershutter").intValue() ):
            return
      
        if getItemState("pOther_Automatic_State_Rollershutter").intValue() == SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN:
            if input['event'].getItemName() == "pOther_Automatic_State_Rollershutter":
                for config in configs:
                    if getItemState(config["contact"]) != CLOSED:
                        continue
                    sendCommand(config["shutter"], DOWN)
        elif getItemState("pOther_Automatic_State_Rollershutter").intValue() == SunProtectionHelper.STATE_ROLLERSHUTTER_UP:
            if getItemState("pOther_Presence_State").intValue() == PresenceHelper.STATE_AWAY:
                sendCommand("gShutters", UP)

@rule()
class RollershutterAutoWindowContact:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gFF_Sensor_Window")
        
        #self.log.info(u"{}".format(math.floor( len(configs) / 2 )))
        #for config in configs:
        #    self.log.info(u"{} {}".format(getItemState(config["shutter"]),getItemState(config["shutter"]).intValue() == 0))

    def execute(self, module, input):
        contactItemName = input['event'].getItemName()
        if contactItemName not in contact_map:
            return
          
        rollershutter_flags = getItemState("pOther_Manual_State_Auto_Rollershutter").intValue()
        config = contact_map[contactItemName]
        state = None
        if input['event'].getItemState() == OPEN:
            state = UP
        else:
            if FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_TIME_DEPENDENT, rollershutter_flags ) and getItemState("pOther_Automatic_State_Rollershutter").intValue() == SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN:
                #closedShutters = 0
                for _config in configs:
                    if getItemState(_config["shutter"]).intValue() == 100:
                        state = DOWN
                        break
                        #closedShutters += 1
                #if closedShutters >= math.floor( len(configs) / 2 ):
                #state = DOWN if closedShutters >
            elif (FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_SHADING, rollershutter_flags ) and "sunprotection" in config and "sunprotectionOnlyIfAway" not in config and getItemState(config["sunprotection"]) == ON):
                state = DOWN

        #self.log.info(str(state))
        #return

        if state is None:
            return
        
        sendCommand(config["shutter"], state)

@rule()
class RollershutterAutoPresence:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Presence_State")]
        self.awayTimer = None

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

        self.awayTimer = None

    def execute(self, module, input):
        if not FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_SHADING, getItemState("pOther_Manual_State_Auto_Rollershutter").intValue() ):
            return
          
        if self.awayTimer != None:
            self.awayTimer.cancel()
            self.awayTimer = None
            
        # Presence state is only related to sun protection.
        # Means, we handle it only if global state is UP
        if getItemState("pOther_Automatic_State_Rollershutter").intValue() in [SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN,SunProtectionHelper.STATE_ROLLERSHUTTER_MAYBE_UP]:
            return
    
        if input['event'].getItemState().intValue() == PresenceHelper.STATE_AWAY:
            self.awayTimer = startTimer(self.log, 1800, self.updateCallback, args = [ DOWN ])
        elif input['event'].getItemState().intValue() == PresenceHelper.STATE_PRESENT and input['event'].getOldItemState().intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
            self.updateCallback(UP)

@rule()
class RollershutterAutoSunprotection:
    def __init__(self):
        self.triggers = []
        for sunprotection_item in sunprotection_map:
            self.triggers.append(ItemStateChangeTrigger(sunprotection_item))

    def execute(self, module, input):
        if not FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_SHADING, getItemState("pOther_Manual_State_Auto_Rollershutter").intValue() ):
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
                if "sunprotectionOnlyIfAway" in config and (getItemState("pOther_Presence_State").intValue() != PresenceHelper.STATE_AWAY or itemLastChangeNewerThen("pOther_Presence_State", ZonedDateTime.now().minusSeconds(1800))):
                    continue
          
            sendCommand(config["shutter"], state)

          
@rule()
class RollershutterTerraceAutoSunprotection:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Terrace")
        ]

    def execute(self, module, input):
        if not FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_SHADING, getItemState("pOther_Manual_State_Auto_Rollershutter").intValue() ):
            return

        if getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == SunProtectionHelper.STATE_TERRACE_MAYBE_CLOSED:
            pass
        elif getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == SunProtectionHelper.STATE_TERRACE_CLOSED:
            # DOWN only if automatic is enabled and (people are present or where present changed recently or terrace door is open)
            if (
                 getItemState("pOther_Presence_State").intValue() not in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]
                 or
                 itemLastChangeNewerThen("pOther_Presence_State", ZonedDateTime.now().minusMinutes(120))
                 or
                 getItemState("pGF_Livingroom_Openingcontact_Window_Terrace_State") == OPEN
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

