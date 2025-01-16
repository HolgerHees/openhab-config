from shared.helper import rule, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged, getItemState, startTimer, getThing, itemLastChangeOlderThen, UserHelper, NotificationHelper
from shared.triggers import CronTrigger, ThingStatusChangeTrigger, ItemCommandTrigger, ItemStateChangeTrigger
from shared.actions import Transformation
from custom.presence import PresenceHelper


TARGET_HUMIDITY = 50.0

MAX_SLEEPING_LEVEL = 1
MAX_PRESENT_LEVEL = 3
MAX_AWAY_LEVEL = 3

@rule()
class HumidifierState:
    def __init__(self):
        self.thing_uid_map = {
            "tuya:tuyaDevice:humidifier_eg": "pGF_Livingroom_Humidifier_Online",
            "tuya:tuyaDevice:humidifier_og": "pFF_Bedroom_Humidifier_Online"
        }

        self.triggers = []
        for thing_uid in self.thing_uid_map.keys():
            self.triggers.append(ThingStatusChangeTrigger(thing_uid))
            startTimer(self.log, 5, self.check, args=[thing_uid,])

    def check(self, thing_uid):
        thing = getThing(thing_uid)
        status = thing.getStatus()
        info = thing.getStatusInfo()

        if status is not None and info is not None:
            if status.toString() != "ONLINE":
                if postUpdateIfChanged(self.thing_uid_map[thing_uid],OFF):
                    self.log.info("Humidifier State Change: {} - {}".format(status.toString(), info.toString()))
            else:
                postUpdateIfChanged(self.thing_uid_map[thing_uid],ON)

    def execute(self, module, input):
        self.check(str(input['event'].getThingUID()))

@rule()
class HumidifierStateReset:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            ItemCommandTrigger("pGF_Livingroom_Humidifier_Filter_Reset"),
            ItemCommandTrigger("pFF_Bedroom_Humidifier_Filter_Reset")
        ]

    def execute(self, module, input):
        postUpdate(input['event'].getItemName(), OFF)

@rule()
class HumidifierStateMessage:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Replace_Filter"),
            ItemStateChangeTrigger("pFF_Bedroom_Humidifier_Replace_Filter"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Fault"),
            ItemStateChangeTrigger("pFF_Bedroom_Humidifier_Fault")
        ]

    def check(self, itemName, itemState):
        item_location = "_".join(itemName.split("_")[:2])

        msg = []
        if "Filter" in itemName and itemState == ON:
            msg.append("Filter")

        if "Fault" in itemName and itemState.intValue() == 1:
            msg.append("Wasser")

        if len(msg) == 0:
            msg.append("Alles ok")

        msg = ", ".join(msg)

        postUpdateIfChanged(u"{}_Humidifier_State_Message".format(item_location), msg)

    def execute(self, module, input):
        self.check(input['event'].getItemName(), input['event'].getItemState())

@rule()
class HumidifierLevel:
    def __init__(self):
        self.sensor_location_map = {
            "pGF_Livingroom_Air_Sensor_Humidity_Value": "pGF_Livingroom",
            "pGF_Corridor_Air_Sensor_Humidity_Value": "pGF_Livingroom",

            "pFF_Dressingroom_Air_Sensor_Humidity_Value": "pFF_Bedroom",
            "pFF_Bedroom_Air_Sensor_Humidity_Value": "pFF_Bedroom"
        #    "pFF_Corridor_Air_Sensor_Humidity_Value": "pFF_Bedroom"
        }

        self.triggers = [
            ItemCommandTrigger("pGF_Livingroom_Humidifier_Speed"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Auto_Mode", state="ON"),

            ItemCommandTrigger("pFF_Bedroom_Humidifier_Speed"),
            ItemStateChangeTrigger("pFF_Bedroom_Humidifier_Auto_Mode", state="ON"),

            ItemStateChangeTrigger("pOther_Presence_State"),
            CronTrigger("0 * * * * ?")
        ]

        for sensor in self.sensor_location_map.keys():
            self.triggers.append(ItemStateChangeTrigger(sensor))

        self.autoChangeInProgress = {
            "pGF_Livingroom": False,
            "pFF_Bedroom": False
        }

        #sendCommand("pGF_Livingroom_Humidifier_Power", REFRESH)

    def execute(self, module, input):
        if input['event'].getType() != "TimerEvent" and "Humidifier_Speed" in input['event'].getItemName():
            item_location = "_".join(input['event'].getItemName().split("_")[:2])

            if self.autoChangeInProgress[item_location]:
                self.autoChangeInProgress[item_location] = False
            else:
                postUpdate(u"{}_Humidifier_Auto_Mode".format(item_location), OFF)
            return

        if input['event'].getType() == "TimerEvent" or input['event'].getItemName() == "pOther_Presence_State":
            humidifier_locations = list(self.autoChangeInProgress.keys())

            if input['event'].getType() == "TimerEvent":
                for humidifier_location in humidifier_locations:
                    # sometimes, if humidifier items are reloaded humidifier target is falling back to 40%
                    sendCommandIfChanged(u"{}_Humidifier_Target".format(humidifier_location), "CO")

                    # sometimes, if humidifier was offline for some seconds, state is powered off
                    #sendCommandIfChanged(u"{}_Humidifier_Power".format(humidifier_location), ON)
        else:
            if input['event'].getItemName() in self.sensor_location_map:
                humidifier_locations = [ self.sensor_location_map[input['event'].getItemName()] ]
            else:
                humidifier_locations = [ "_".join(input['event'].getItemName().split("_")[:2]) ]

        for humidifier_location in humidifier_locations:
            if getItemState(u"{}_Humidifier_Auto_Mode".format(humidifier_location)) == OFF:
                continue

            if getItemState(u"{}_Humidifier_Online".format(humidifier_location)) == OFF:
                continue

            currentLevel = int(getItemState(u"{}_Humidifier_Speed".format(humidifier_location)).toString()[-1])
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
            for sensor, location in self.sensor_location_map.items():
                if humidifier_location != location:
                    continue

                _humidity = getItemState(sensor).doubleValue()
                if _humidity < humidity:
                    humidity = _humidity

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

            #self.log.info("{} {} {} {}".format(humidifier_location, humidity, currentLevel, newLevel))

            if newLevel > maxLevel:
                newLevel = maxLevel

            if newLevel != currentLevel:
                # 1. input['event'].getType() != "TimerEvent" is an presence or auto mode change
                # 2. is cron triggered event
                # => itemLastChangeOlderThen check to prevent level flapping on humidity changes
                if input['event'].getType() != "TimerEvent" or itemLastChangeOlderThen(u"{}_Humidifier_Speed".format(humidifier_location), ZonedDateTime.now().minusMinutes(15)):
                    self.autoChangeInProgress[humidifier_location] = True

                    sendCommand(u"{}_Humidifier_Speed".format(humidifier_location), "level_{}".format(newLevel))
