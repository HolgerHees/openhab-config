from shared.helper import rule, postUpdate, postUpdateIfChanged, sendCommand, getItemState, getThing, itemLastChangeOlderThen
from shared.triggers import CronTrigger, ThingStatusChangeTrigger, ItemCommandTrigger, ItemStateChangeTrigger

from custom.presence import PresenceHelper

from org.openhab.core.types import UnDefType

REFERENCE_SENSORS = ["pGF_Livingroom_Air_Sensor_Humidity_Value", "pGF_Corridor_Air_Sensor_Humidity_Value"]
TARGET_HUMIDITY = 55

MAX_SLEEPING_LEVEL = 1
MAX_PRESENT_LEVEL = 3
MAX_AWAY_LEVEL = 3

@rule("humidifier.py")
class HumidifierStateRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ThingStatusChangeTrigger("tuya:tuyaDevice:humidifier")
        ]
        self.check()

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

@rule("humidifier.py")
class HumidifierStateResetRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemCommandTrigger("pGF_Livingroom_Humidifier_Filter_Reset")
        ]

    def execute(self, module, input):
        postUpdateIfChanged(input['event'].getItemName(), 0)

@rule("humidifier.py")
class HumidifierStateMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Fault"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Replace_Filter")
        ]
        self.check()

        #postUpdateIfChanged("pGF_Livingroom_Humidifier_Replace_Filter", OFF)

    def check(self):
        active = []

        if isinstance(getItemState("pGF_Livingroom_Humidifier_Fault"), UnDefType) \
            or isinstance(getItemState("pGF_Livingroom_Humidifier_Replace_Filter"), UnDefType):
                return


        if getItemState("pGF_Livingroom_Humidifier_Replace_Filter") == ON:
            active.append(u"Filter")

        if getItemState("pGF_Livingroom_Humidifier_Fault").intValue() != 0:
            active.append(u"Fehler")

        if len(active) == 0:
            active.append(u"Alles ok")

        msg = ", ".join(active)

        postUpdateIfChanged("pGF_Livingroom_Humidifier_State_Message", msg)

    def execute(self, module, input):
        self.check()

@rule("humidifier.py")
class HumidifierLevelRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("pGF_Livingroom_Humidifier_Speed"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Auto_Mode", state="ON"),
            ItemStateChangeTrigger("pOther_Presence_State"),
            CronTrigger("0 */1 * * * ?")
        ]

        for sensor in REFERENCE_SENSORS:
            self.triggers.append(ItemStateChangeTrigger(sensor))

        self.autoChangeInProgress = False
        self.activeLevel = -1

    def execute(self, module, input):
        if 'event' in input.keys() and input['event'].getItemName() == "pGF_Livingroom_Humidifier_Speed":
            if self.autoChangeInProgress:
                self.autoChangeInProgress = False
            else:
                postUpdate("pGF_Livingroom_Humidifier_Auto_Mode", OFF)
            return

        if getItemState("pGF_Livingroom_Humidifier_Auto_Mode") == OFF or getItemState("pGF_Livingroom_Humidifier_Online") == OFF:
            return

        if isinstance(getItemState("pGF_Livingroom_Humidifier_Speed"), UnDefType):
            return

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
            _humidity = getItemState(sensor).intValue()
            if _humidity < humidity:
                humidity = _humidity

        flappingProtectionDiff = ( (currentLevel -1) * 2) / 10.0

        if TARGET_HUMIDITY - humidity < (3 - flappingProtectionDiff):
            newLevel = 1
        elif TARGET_HUMIDITY - humidity < (7 - flappingProtectionDiff):
            newLevel = 2
        else:
            newLevel = 3

        if newLevel > maxLevel:
            newLevel = maxLevel

        if newLevel != currentLevel:
            # 1. 'event' in input.keys() is an presence or auto mode change
            # 2. is cron triggered event
            # => itemLastChangeOlderThen check to prevent level flapping on humidity changes
            if 'event' in input.keys() or itemLastChangeOlderThen("pGF_Livingroom_Humidifier_Speed", ZonedDateTime.now().minusMinutes(15)):
                self.autoChangeInProgress = True

                sendCommand("pGF_Livingroom_Humidifier_Speed", "level_{}".format(newLevel))
