import math

from custom.helper import rule, getNow, itemLastChangeOlderThen, getItemState, postUpdate, postUpdateIfChanged, \
    sendCommand, startTimer
from core.triggers import CronTrigger, ItemCommandTrigger, ItemStateChangeTrigger

autoChangeInProgress = False

DELAYED_UPDATE_TIMEOUT = 3

@rule("ventilation_efficiency.py")
class VentilationEfficiencyRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Ventilation_Outdoor_Incoming_Temperature"),
            ItemStateChangeTrigger("Ventilation_Indoor_Incoming_Temperature"),
            ItemStateChangeTrigger("Ventilation_Indoor_Outgoing_Temperature")
        ]
        self.updateTimer = None
    
    def delayUpdate(self):
        efficiency = 0

        if getItemState("Ventilation_Bypass") == OFF:
            tempOutIn = getItemState("Ventilation_Outdoor_Incoming_Temperature").doubleValue()
            tempInOut = getItemState("Ventilation_Indoor_Outgoing_Temperature").doubleValue()
            tempInIn = getItemState("Ventilation_Indoor_Incoming_Temperature").doubleValue()

            if tempInOut != tempOutIn:
                efficiency = ( tempInIn - tempOutIn ) / ( tempInOut - tempOutIn ) * 100
                efficiency = round( efficiency );
            else:
                efficiency = 100
        else:
            efficiency = 0

        postUpdateIfChanged("Ventilation_Bypass_Efficiency", efficiency )

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))
        
@rule("ventilation_control.py")
class FilterRuntimeRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Ventilation_Filter_Runtime")]

    def execute(self, module, input):
        laufzeit = getItemState("Ventilation_Filter_Runtime").doubleValue()

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

        postUpdateIfChanged("Ventilation_Filter_Runtime_Message", msg)
 
@rule("ventilation_control.py")
class FilterStateMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Ventilation_Error_Message"),
            ItemStateChangeTrigger("Ventilation_Filter_Error")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        active = []

        if getItemState("Ventilation_Filter_Error") == ON:
            active.append(u"Filter")

        if getItemState("Ventilation_Error_Message").toString() != "No Errors":
            active.append(u"Error: {}".format( getItemState("Ventilation_Error_Message").toString() ))

        if len(active) == 0:
            active.append(u"Alles in Ordnung")

        msg = ", ".join(active)

        postUpdateIfChanged("Ventilation_State_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("ventilation_control.py")
class FilterOutdoorTemperatureMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Ventilation_Outdoor_Incoming_Temperature"),
            ItemStateChangeTrigger("Ventilation_Outdoor_Outgoing_Temperature")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"→ {}°C, ← {}°C".format(getItemState("Ventilation_Outdoor_Incoming_Temperature").format("%.1f"),getItemState("Ventilation_Outdoor_Outgoing_Temperature").format("%.1f"))
        postUpdateIfChanged("Ventilation_Outdoor_Temperature_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("ventilation_control.py")
class FilterIndoorTemperatureMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Ventilation_Indoor_Incoming_Temperature"),
            ItemStateChangeTrigger("Ventilation_Indoor_Outgoing_Temperature")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"→ {}°C, ← {}°C".format(getItemState("Ventilation_Indoor_Incoming_Temperature").format("%.1f"),getItemState("Ventilation_Indoor_Outgoing_Temperature").format("%.1f"))
        postUpdateIfChanged("Ventilation_Indoor_Temperature_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("ventilation_control.py")
class FilterVentilationMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Ventilation_Incoming"),
            ItemStateChangeTrigger("Ventilation_Outgoing")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"→ {}%, ← {}%".format(getItemState("Ventilation_Incoming").toString(),getItemState("Ventilation_Outgoing").toString())
        postUpdateIfChanged("Ventilation_Fan_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("ventilation_control.py")
class FilterManualActionRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Ventilation_Fan_Level")]

    def execute(self, module, input):
        global autoChangeInProgress
        if autoChangeInProgress:
            autoChangeInProgress = False
        else:
            postUpdate("Ventilation_Auto_Mode", OFF)


@rule("ventilation_control.py")
class FilterFanLevelRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Ventilation_Auto_Mode"),
            ItemStateChangeTrigger("State_Presence"),
            CronTrigger("0 */1 * * * ?"),
        ]

    def execute(self, module, input):
        if getItemState("Ventilation_Auto_Mode") == OFF:
            return

        currentLevel = getItemState("Ventilation_Fan_Level").intValue()

        raumTemperatur = getItemState("Temperature_FF_Livingroom").doubleValue()
        zielTemperatur = getItemState("Ventilation_Comfort_Temperature").doubleValue
        
        presenceSate = getItemState("State_Presence").intValue()
        
        isTooWarm = raumTemperatur >= zielTemperatur
        
        outdoorTemperatureItemName = getItemState("Outdoor_Temperature_Item_Name").toString()
        coolingPossible = getItemState(outdoorTemperatureItemName).doubleValue() < raumTemperatur

        # Sleep
        if presenceSate == 2:
            reducedLevel = 2    # Level 1
            defaultLevel = 2    # Level 1
            coolingLevel = 2    # Level 1
        # Away since 30 minutes
        elif presenceSate == 0 and itemLastChangeOlderThen("State_Presence", getNow().minusMinutes(60)):
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
            # Wenn der aktuelle Level Stufe 'A' (also 1) ist, sollte vor einem erneuten umschalten gewartet werden damit ein
            # hin und herschalten vermieden wird. z.B. bei kurzzeitigen Temperaturschwankungen
            if currentLevel == 1:
                waitBeforeChange = 15
            else:
                # must be > 1. Otherwise cangedSince dows not work propperly
                waitBeforeChange = 2

            isModeUpdate = 'event' in input.keys() and input['event'].getItemName() == "Ventilation_Auto_Mode"
            
            if isModeUpdate or itemLastChangeOlderThen("Ventilation_Fan_Level", getNow().minusMinutes(waitBeforeChange)):
                global autoChangeInProgress
                autoChangeInProgress = True

                sendCommand("Ventilation_Fan_Level", newLevel)
