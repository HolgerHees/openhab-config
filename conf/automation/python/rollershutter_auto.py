from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from custom.presence import PresenceHelper
from custom.sunprotection import SunProtectionHelper
from custom.flags import FlagHelper

from datetime import datetime, timedelta
import math
import threading

import scope


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

@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Automatic_State_Rollershutter"),
        ItemStateChangeTrigger("pOther_Presence_State", state=PresenceHelper.STATE_AWAY)
    ]
)
class MorningEvening:
    def execute(self, module, input):
        if not FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_TIME_DEPENDENT, Registry.getItemState("pOther_Manual_State_Auto_Rollershutter").intValue() ):
            return
      
        if Registry.getItemState("pOther_Automatic_State_Rollershutter").intValue() == SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN:
            if input['event'].getItemName() == "pOther_Automatic_State_Rollershutter":
                for config in configs:
                    if Registry.getItemState(config["contact"]) != scope.CLOSED:
                        continue
                    Registry.getItem(config["shutter"]).sendCommand(scope.DOWN)
        elif Registry.getItemState("pOther_Automatic_State_Rollershutter").intValue() == SunProtectionHelper.STATE_ROLLERSHUTTER_UP:
            if Registry.getItemState("pOther_Presence_State").intValue() == PresenceHelper.STATE_AWAY:
                Registry.getItem("gShutters").sendCommand(scope.UP)

@rule
class WindowContact:
    def buildTriggers(self):
        triggers = []
        for item in Registry.getItem("gGF_Sensor_Window").getAllMembers():
            triggers.append(ItemStateChangeTrigger(item.getName()))
        for item in Registry.getItem("gFF_Sensor_Window").getAllMembers():
            triggers.append(ItemStateChangeTrigger(item.getName()))
        return triggers

    def execute(self, module, input):
        contact_item_name = input['event'].getItemName()
        if contact_item_name not in contact_map:
            return
          
        rollershutter_flags = Registry.getItemState("pOther_Manual_State_Auto_Rollershutter").intValue()
        config = contact_map[contact_item_name]
        state = None
        if input['event'].getItemState() == scope.OPEN:
            state = scope.UP
        else:
            if FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_TIME_DEPENDENT, rollershutter_flags ) and Registry.getItemState("pOther_Automatic_State_Rollershutter").intValue() == SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN:
                #closedShutters = 0
                for _config in configs:
                    if Registry.getItemState(_config["shutter"]).intValue() == 100:
                        state = scope.DOWN
                        break
                        #closedShutters += 1
                #if closedShutters >= math.floor( len(configs) / 2 ):
                #state = DOWN if closedShutters >
            elif (FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_SHADING, rollershutter_flags ) and "sunprotection" in config and "sunprotectionOnlyIfAway" not in config and Registry.getItemState(config["sunprotection"]) == scope.ON):
                state = scope.DOWN

        #self.logger.info(str(state))
        #return

        if state is None:
            return

        Registry.getItem(config["shutter"]).sendCommandIfDifferent(state)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Presence_State")
    ]
)
class Presence:
    def __init__(self):
        self.away_timer = None

    def updateCallback(self,state):
        for config in configs:
            # handle only shutters which depends on presence state
            if "sunprotectionOnlyIfAway" not in config:
                continue

            if state == scope.DOWN:
                if Registry.getItemState(config["contact"]) != scope.CLOSED:
                    continue

                if Registry.getItemState(config["sunprotection"]) != scope.ON:
                    continue

            Registry.getItem(config["shutter"]).sendCommandIfDifferent(state)

        self.away_timer = None

    def execute(self, module, input):
        if not FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_SHADING, Registry.getItemState("pOther_Manual_State_Auto_Rollershutter").intValue() ):
            return
          
        if self.away_timer != None:
            self.away_timer.cancel()
            self.away_timer = None
            
        # Presence state is only related to sun protection.
        # Means, we handle it only if global state is UP
        if Registry.getItemState("pOther_Automatic_State_Rollershutter").intValue() in [SunProtectionHelper.STATE_ROLLERSHUTTER_DOWN,SunProtectionHelper.STATE_ROLLERSHUTTER_MAYBE_UP]:
            return
    
        if input['event'].getItemState().intValue() == PresenceHelper.STATE_AWAY:
            self.away_timer = threading.Timer(1800, self.updateCallback, args = [ scope.DOWN ])
            self.away_timer.start()
        elif input['event'].getItemState().intValue() == PresenceHelper.STATE_PRESENT and input['event'].getOldItemState().intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
            self.updateCallback(scope.UP)

@rule()
class Sunprotection:
    def buildTriggers(self):
        triggers = []
        for sunprotection_item in sunprotection_map:
            triggers.append(ItemStateChangeTrigger(sunprotection_item))
        return triggers

    def execute(self, module, input):
        if not FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_SHADING, Registry.getItemState("pOther_Manual_State_Auto_Rollershutter").intValue() ):
            return
          
        sunprotectionItemName = input['event'].getItemName()
        configs = sunprotection_map[sunprotectionItemName]
        state = scope.DOWN if input['event'].getItemState() == scope.ON else scope.UP
        
        for config in configs:
            if state == scope.DOWN:
                # shutdown shutters only if the window is closed
                if Registry.getItemState(config["contact"]) != scope.CLOSED:
                    continue
                
                # skip closing shutters if we must be away but we are still present or not long enough away
                if "sunprotectionOnlyIfAway" in config and (Registry.getItemState("pOther_Presence_State").intValue() != PresenceHelper.STATE_AWAY or Registry.getItem("pOther_Presence_State").getLastStateChange() > datetime.now().astimezone() - timedelta(seconds=1800)):
                    continue
          
            Registry.getItem(config["shutter"]).sendCommandIfDifferent(state)

          
@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Terrace")
    ]
)
class TerraceAutoSunprotection:
    def execute(self, module, input):
        if not FlagHelper.hasFlag( FlagHelper.AUTO_ROLLERSHUTTER_SHADING, Registry.getItemState("pOther_Manual_State_Auto_Rollershutter").intValue() ):
            return

        if Registry.getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == SunProtectionHelper.STATE_TERRACE_MAYBE_CLOSED:
            pass
        elif Registry.getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == SunProtectionHelper.STATE_TERRACE_CLOSED:
            # DOWN only if automatic is enabled and (people are present or where present changed recently or terrace door is open)
            if (
                 Registry.getItemState("pOther_Presence_State").intValue() not in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]
                 or
                 Registry.getItem("pOther_Presence_State").getLastStateChange() > datetime.now().astimezone() - timedelta(minutes=120)
                 or
                 Registry.getItemState("pGF_Livingroom_Openingcontact_Window_Terrace_State") == scope.OPEN
               ):
                #self.logger.info("down")
                Registry.getItem("pOutdoor_Terrace_Shading_Left_Control").sendCommandIfDifferent(scope.DOWN)
                Registry.getItem("pOutdoor_Terrace_Shading_Right_Control").sendCommandIfDifferent(scope.DOWN)
        else:
            #self.logger.info("up")
            # UP always when sun protection time is over
            Registry.getItem("pOutdoor_Terrace_Shading_Left_Control").sendCommandIfDifferent(scope.UP)
            Registry.getItem("pOutdoor_Terrace_Shading_Right_Control").sendCommandIfDifferent(scope.UP)

#sendCommand("pOther_Automatic_State_Sunprotection_Terrace", 0)

