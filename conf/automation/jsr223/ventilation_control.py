import math
from java.time import ZonedDateTime

from shared.helper import rule, itemLastChangeOlderThen, getItemState, postUpdate, postUpdateIfChanged, sendCommand, startTimer, getThing
from shared.triggers import CronTrigger, ItemCommandTrigger, ItemStateChangeTrigger, ThingStatusChangeTrigger

from custom.presence import PresenceHelper

from org.openhab.core.types import UnDefType


DELAYED_UPDATE_TIMEOUT = 3
 
@rule()
class VentilationControlStateReset:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemCommandTrigger("pGF_Utilityroom_Ventilation_Filter_Reset"),
            ItemCommandTrigger("pGF_Utilityroom_Ventilation_Error_Reset")
        ]

    def execute(self, module, input):
        postUpdateIfChanged(input['event'].getItemName(), 0)

@rule()
class VentilationControlErrorMessage:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ThingStatusChangeTrigger("comfoair:comfoair:default"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Error")
        ]

        startTimer(self.log, 5, self.update)

    def update(self):
        thing = getThing("comfoair:comfoair:default")
        status = thing.getStatus()
        if status.toString() != "ONLINE":
            info = thing.getStatusInfo()
            postUpdateIfChanged("eOther_Error_Ventilation_Message", u"Thing: {}".format( info.toString() ))
        elif getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() != "No Errors":
            postUpdateIfChanged("eOther_Error_Ventilation_Message", getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() )
        else:
            postUpdateIfChanged("eOther_Error_Ventilation_Message", "")

    def execute(self, module, input):
        self.update()

@rule()
class VentilationControlStateMessage:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Error_Message"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Error")
        ]
        self.update()

    def update(self):
        if getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() != "No Errors":
            msg = u"Error"
        elif getItemState("pGF_Utilityroom_Ventilation_Filter_Error") == ON:
            msg = u"Filter"
        else:
            msg = u"Alles ok"

        postUpdateIfChanged("pGF_Utilityroom_Ventilation_State_Message", msg)

    def execute(self, module, input):
        self.update()

@rule()
class VentilationControlEfficiency:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature")
        ]
        self.updateTimer = None
    
    def delayUpdate(self):
        efficiency = 0

        if getItemState("pGF_Utilityroom_Ventilation_Bypass") == OFF:
            if isinstance(getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"), UnDefType) \
              or isinstance(getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature"), UnDefType) \
              or isinstance(getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"), UnDefType):
                  return
                
            tempOutIn = getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature").doubleValue()
            tempInOut = getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature").doubleValue()
            tempInIn = getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature").doubleValue()

            if tempInOut != tempOutIn:
                efficiency = ( tempInIn - tempOutIn ) / ( tempInOut - tempOutIn ) * 100
                efficiency = round( efficiency );
            else:
                efficiency = 100
        else:
            efficiency = 0

        postUpdateIfChanged("pGF_Utilityroom_Ventilation_Bypass_Efficiency", efficiency )

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))
        
@rule()
class VentilationControlRuntime:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Runtime")]

    def execute(self, module, input):
        if isinstance(input['event'].getItemState(), UnDefType):
            return
      
        laufzeit = input['event'].getItemState().doubleValue()

        weeks = int(math.floor(laufzeit / 168.0))
        days = int(math.floor((laufzeit - (weeks * 168.0)) / 24))

        active = []
        if weeks > 0:
            if weeks == 1:
                active.append(u"1 Woche")
            else:
                active.append(u"{} Wochen".format(weeks))

        if days > 0:
            if days == 1:
                active.append(u"1 Tag")
            else:
                active.append(u"{} Tage".format(days))

        msg = u", ".join(active)

        postUpdateIfChanged("pGF_Utilityroom_Ventilation_Filter_Runtime_Message", msg)
 
@rule()
class VentilationControlOutdoorTemperatureMessage:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        if isinstance(getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"), UnDefType) \
            or isinstance(getItemState("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature"), UnDefType):
                return

        msg = u"→ {}°C, ← {}°C".format(getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature").format("%.1f"),getItemState("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature").format("%.1f"))
        postUpdateIfChanged("pGF_Utilityroom_Ventilation_Outdoor_Temperature_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule()
class VentilationControlIndoorTemperatureMessage:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        if isinstance(getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"), UnDefType) \
            or isinstance(getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature"), UnDefType):
                return

        msg = u"→ {}°C, ← {}°C".format(getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature").format("%.1f"),getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature").format("%.1f"))
        postUpdateIfChanged("pGF_Utilityroom_Ventilation_Indoor_Temperature_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule()
class VentilationControlFilterMessage:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Incoming"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outgoing")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        if isinstance(getItemState("pGF_Utilityroom_Ventilation_Incoming"), UnDefType) \
            or isinstance(getItemState("pGF_Utilityroom_Ventilation_Outgoing"), UnDefType):
                return

        msg = u"→ {}%, ← {}%".format(getItemState("pGF_Utilityroom_Ventilation_Incoming").toString(),getItemState("pGF_Utilityroom_Ventilation_Outgoing").toString())
        postUpdateIfChanged("pGF_Utilityroom_Ventilation_Fan_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule()
class VentilationControlFanLevelRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("pGF_Utilityroom_Ventilation_Fan_Level"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Auto_Mode", state="ON"),
            ItemStateChangeTrigger("pOther_Presence_State"),
            CronTrigger("0 */1 * * * ?"),
        ]
        
        self.autoChangeInProgress = False
        self.activeLevel = -1

    def execute(self, module, input):
        if 'event' in input.keys() and input['event'].getItemName() == "pGF_Utilityroom_Ventilation_Fan_Level":
            if self.autoChangeInProgress:
                self.autoChangeInProgress = False
            else:
                postUpdate("pGF_Utilityroom_Ventilation_Auto_Mode", OFF)
            return

        if getItemState("pGF_Utilityroom_Ventilation_Auto_Mode") == OFF:
            return

        if isinstance(getItemState("pGF_Utilityroom_Ventilation_Fan_Level"), UnDefType) or isinstance(getItemState("pGF_Utilityroom_Ventilation_Comfort_Temperature"), UnDefType):
            return

        currentLevel = getItemState("pGF_Utilityroom_Ventilation_Fan_Level").intValue()
        if self.activeLevel == -1:
            self.activeLevel = currentLevel
        
        raumTemperatur = getItemState("pGF_Livingroom_Air_Sensor_Temperature_Value").doubleValue()
        zielTemperatur = getItemState("pGF_Utilityroom_Ventilation_Comfort_Temperature").doubleValue
        
        presenceState = getItemState("pOther_Presence_State").intValue()
        
        isTooWarm = raumTemperatur >= zielTemperatur
        
        outdoorTemperatureItemName = getItemState("pOutdoor_WeatherStation_Temperature_Item_Name").toString()
        coolingPossible = getItemState(outdoorTemperatureItemName).doubleValue() < raumTemperatur

        # Sleep
        if presenceState in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
            reducedLevel = 2    # Level 1
            defaultLevel = 2    # Level 1
            coolingLevel = 2    # Level 1
        # Away since 60 minutes
        elif presenceState == [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT] and itemLastChangeOlderThen("pOther_Presence_State", ZonedDateTime.now().minusMinutes(60)):
            reducedLevel = 1    # Level A
            defaultLevel = 2    # Level 1
            coolingLevel = 3    # Level 2
        else:
            reducedLevel = 2    # Level 1
            defaultLevel = 3    # Level 2
            coolingLevel = 3    # Level 2
            
        # reducedLevel if it is too warm inside and also outside
        # coolingLevel if it is too warm inside but outside colder then inside
        newLevel = (coolingLevel if coolingPossible else reducedLevel) if isTooWarm else defaultLevel

        if newLevel != currentLevel:
            # 1. self.activeLevel != currentLevel means last try was not successful
            # 2. 'event' in input.keys() is an presence or auto mode change
            # 3. is cron triggered event
            # => itemLastChangeOlderThen check to prevent level flapping on temperature changes
            if self.activeLevel != currentLevel or 'event' in input.keys() or itemLastChangeOlderThen("pGF_Utilityroom_Ventilation_Fan_Level", ZonedDateTime.now().minusMinutes(15)):
                self.autoChangeInProgress = True

                sendCommand("pGF_Utilityroom_Ventilation_Fan_Level", newLevel)
                self.activeLevel = newLevel
