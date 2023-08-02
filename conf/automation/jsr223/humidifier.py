from shared.helper import rule, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged, getItemState, startTimer, getThing, itemLastChangeOlderThen
from shared.triggers import CronTrigger, ThingStatusChangeTrigger, ItemCommandTrigger, ItemStateChangeTrigger
from custom.presence import PresenceHelper


REFERENCE_SENSORS = ["pGF_Livingroom_Air_Sensor_Humidity_Value", "pGF_Corridor_Air_Sensor_Humidity_Value"]
TARGET_HUMIDITY = 50.0

MAX_SLEEPING_LEVEL = 1
MAX_PRESENT_LEVEL = 3
MAX_AWAY_LEVEL = 3

@rule()
class HumidifierState:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ThingStatusChangeTrigger("tuya:tuyaDevice:humidifier")
        ]

        startTimer(self.log, 5, self.check)

    def check(self):
        thing = getThing("tuya:tuyaDevice:humidifier")
        status = thing.getStatus()
        info = thing.getStatusInfo()

        if status is not None and info is not None:
            if status.toString() != "ONLINE":
                self.log.info("Humidifier State Change: {} - {}".format(status.toString(), info.toString()))
                postUpdateIfChanged("pGF_Livingroom_Humidifier_Online",OFF)
            else:
                postUpdateIfChanged("pGF_Livingroom_Humidifier_Online",ON)

    def execute(self, module, input):
        self.check()

@rule()
class HumidifierStateReset:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemCommandTrigger("pGF_Livingroom_Humidifier_Filter_Reset")
        ]

    def execute(self, module, input):
        postUpdateIfChanged(input['event'].getItemName(), 0)

@rule()
class HumidifierStateMessage:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Fault"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Replace_Filter")
        ]
        self.check()

        #postUpdateIfChanged("pGF_Livingroom_Humidifier_Fault", 0)

    def check(self):
        if getItemState("pGF_Livingroom_Humidifier_Fault").intValue() != 0:
            msg = Transformation.transform("MAP", "tuya_humidifier_fault.map", getItemState("pGF_Livingroom_Humidifier_Fault").toString() )
        elif getItemState("pGF_Livingroom_Humidifier_Replace_Filter") == ON:
            msg = u"Filter"
        else:
            msg = u"Alles ok"

        postUpdateIfChanged("pGF_Livingroom_Humidifier_State_Message", msg)

    def execute(self, module, input):
        self.check()

@rule()
class HumidifierLevel:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("pGF_Livingroom_Humidifier_Speed"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Auto_Mode", state="ON"),
            ItemStateChangeTrigger("pOther_Presence_State"),
            CronTrigger("0 * * * * ?")
        ]

        for sensor in REFERENCE_SENSORS:
            self.triggers.append(ItemStateChangeTrigger(sensor))

        self.autoChangeInProgress = False
        self.activeLevel = -1

        #sendCommand("pGF_Livingroom_Humidifier_Power", REFRESH)

    def execute(self, module, input):
        if input['event'].getType() != "TimerEvent" and input['event'].getItemName() == "pGF_Livingroom_Humidifier_Speed":
            if self.autoChangeInProgress:
                self.autoChangeInProgress = False
            else:
                postUpdate("pGF_Livingroom_Humidifier_Auto_Mode", OFF)
            return

        if getItemState("pGF_Livingroom_Humidifier_Auto_Mode") == OFF:
            return

        if getItemState("pGF_Livingroom_Humidifier_Online") == OFF:
            return

        # sometimes, if humidifier was offline for some seconds, state is powered off
        sendCommandIfChanged("pGF_Livingroom_Humidifier_Power", ON)

        currentLevel = int(getItemState("pGF_Livingroom_Humidifier_Speed").toString()[-1])
        if self.activeLevel == -1:
            self.activeLevel = currentLevel
        presenceState = getItemState("pOther_Presence_State").intValue()

        # Sleep
        if presenceState in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
            maxLevel = MAX_SLEEPING_LEVEL
        # Away since 60 minutes
        elif presenceState == [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT] and itemLastChangeOlderThen("pOther_Presence_State", ZonedDateTime.now().minusMinutes(60)):
            maxLevel = MAX_AWAY_LEVEL
        else:
            maxLevel = MAX_PRESENT_LEVEL

        humidity = 100
        for sensor in REFERENCE_SENSORS:
            _humidity = getItemState(sensor).doubleValue()
            if _humidity < humidity:
                humidity = _humidity

        #self.log.info("{} {}".format(TARGET_HUMIDITY - humidity, (0 - ( 5 if currentLevel > 1 else 0))))

        # slowdown, if humidity >= 55
        # speedup if humidity <= 50
        if TARGET_HUMIDITY - humidity <= (0 - ( 5 if currentLevel > 1 else 0) ):
            newLevel = 1
        # slowdown, if humidity >= 50
        # speedup if humidity <= 45
        elif TARGET_HUMIDITY - humidity <= (5 - ( 5 if currentLevel > 2 else 0) ):
            newLevel = 2
        else:
            newLevel = 3

        if newLevel > maxLevel:
            newLevel = maxLevel

        if newLevel != currentLevel:
            # 1. input['event'].getType() != "TimerEvent" is an presence or auto mode change
            # 2. is cron triggered event
            # => itemLastChangeOlderThen check to prevent level flapping on humidity changes
            if input['event'].getType() != "TimerEvent" or itemLastChangeOlderThen("pGF_Livingroom_Humidifier_Speed", ZonedDateTime.now().minusMinutes(15)):
                self.autoChangeInProgress = True

                sendCommand("pGF_Livingroom_Humidifier_Speed", "level_{}".format(newLevel))
