import math
from java.time import ZonedDateTime

from shared.helper import rule, itemLastChangeOlderThen, getItemState, postUpdate, postUpdateIfChanged, sendCommand, startTimer, getThing, sendNotificationToAllAdmins
from shared.triggers import CronTrigger, ItemCommandTrigger, ItemStateChangeTrigger, ThingStatusChangeTrigger


autoChangeInProgress = False

DELAYED_UPDATE_TIMEOUT = 3

@rule("ventilation_control.py")
class VentilationStateMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Error_Message"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Error"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Thing_State")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        active = []

        if getItemState("pGF_Utilityroom_Ventilation_Filter_Error") == ON:
            active.append(u"Filter")

        if getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() != "No Errors":
            active.append(u"Error: {}".format( getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() ))

        if getItemState("pGF_Utilityroom_Ventilation_Thing_State").toString() != "Alles ok":
            active.append(u"Error: {}".format( getItemState("pGF_Utilityroom_Ventilation_Thing_State").toString() ))

        if len(active) == 0:
            active.append(u"Alles ok")

        msg = ", ".join(active)

        postUpdateIfChanged("pGF_Utilityroom_Ventilation_State_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("ventilation_state.py")
class VentilationStateRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ThingStatusChangeTrigger("comfoair:comfoair:default")
        ]
        self.check()
        
    def check(self):
        thing = getThing("comfoair:comfoair:default")
        status = thing.getStatus()
        info = thing.getStatusInfo()
        
        #self.log.info(u"{}".format(status))

        if status is not None and info is not None:
            if status.toString() == 'OFFLINE':
                postUpdateIfChanged("pGF_Utilityroom_Ventilation_Thing_State",info.toString())
            else:
                postUpdateIfChanged("pGF_Utilityroom_Ventilation_Thing_State","Alles ok")

    def execute(self, module, input):
        self.check()

@rule("ventilation_efficiency.py")
class VentilationEfficiencyRule:
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
        
@rule("ventilation_control.py")
class FilterRuntimeRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Runtime")]

    def execute(self, module, input):
        laufzeit = getItemState("pGF_Utilityroom_Ventilation_Filter_Runtime").doubleValue()

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
 
@rule("ventilation_control.py")
class FilterOutdoorTemperatureMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"→ {}°C, ← {}°C".format(getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature").format("%.1f"),getItemState("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature").format("%.1f"))
        postUpdateIfChanged("pGF_Utilityroom_Ventilation_Outdoor_Temperature_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("ventilation_control.py")
class FilterIndoorTemperatureMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"→ {}°C, ← {}°C".format(getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature").format("%.1f"),getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature").format("%.1f"))
        postUpdateIfChanged("pGF_Utilityroom_Ventilation_Indoor_Temperature_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("ventilation_control.py")
class FilterVentilationMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Incoming"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outgoing")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"→ {}%, ← {}%".format(getItemState("pGF_Utilityroom_Ventilation_Incoming").toString(),getItemState("pGF_Utilityroom_Ventilation_Outgoing").toString())
        postUpdateIfChanged("pGF_Utilityroom_Ventilation_Fan_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("ventilation_control.py")
class FilterManualActionRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("pGF_Utilityroom_Ventilation_Fan_Level")]

    def execute(self, module, input):
        global autoChangeInProgress
        if autoChangeInProgress:
            autoChangeInProgress = False
        else:
            postUpdate("pGF_Utilityroom_Ventilation_Auto_Mode", OFF)


@rule("ventilation_control.py")
class FilterFanLevelRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Auto_Mode"),
            ItemStateChangeTrigger("pOther_Presence_State"),
            CronTrigger("0 */1 * * * ?"),
        ]

    def execute(self, module, input):
        if getItemState("pGF_Utilityroom_Ventilation_Auto_Mode") == OFF:
            return

        currentLevel = getItemState("pGF_Utilityroom_Ventilation_Fan_Level").intValue()

        raumTemperatur = getItemState("pGF_Livingroom_Air_Sensor_Temperature_Value").doubleValue()
        zielTemperatur = getItemState("pGF_Utilityroom_Ventilation_Comfort_Temperature").doubleValue
        
        presenceSate = getItemState("pOther_Presence_State").intValue()
        
        isTooWarm = raumTemperatur >= zielTemperatur
        
        outdoorTemperatureItemName = getItemState("pOutdoor_WeatherStation_Temperature_Item_Name").toString()
        coolingPossible = getItemState(outdoorTemperatureItemName).doubleValue() < raumTemperatur

        # Sleep
        if presenceSate == 2:
            reducedLevel = 2    # Level 1
            defaultLevel = 2    # Level 1
            coolingLevel = 2    # Level 1
        # Away since 30 minutes
        elif presenceSate == 0 and itemLastChangeOlderThen("pOther_Presence_State", ZonedDateTime.now().minusMinutes(60)):
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

            isModeUpdate = 'event' in input.keys() and input['event'].getItemName() == "pGF_Utilityroom_Ventilation_Auto_Mode"
            
            if isModeUpdate or itemLastChangeOlderThen("pGF_Utilityroom_Ventilation_Fan_Level", ZonedDateTime.now().minusMinutes(waitBeforeChange)):
                global autoChangeInProgress
                autoChangeInProgress = True

                sendCommand("pGF_Utilityroom_Ventilation_Fan_Level", newLevel)
