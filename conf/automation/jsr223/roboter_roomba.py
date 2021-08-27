import time
from java.time import ZonedDateTime

from shared.helper import rule, itemLastChangeOlderThen, getItemState, sendNotification, postUpdate, postUpdateIfChanged, sendCommand
from shared.triggers import CronTrigger, ItemStateChangeTrigger

from custom.presence import PresenceHelper


@rule("roboter_roomba.py")
class RoombaBoostControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pIndoor_Roomba_boost")]

    def execute(self, module, input):
        state = getItemState("pIndoor_Roomba_boost").toString()

        if state == "eco":
            sendCommand("pIndoor_Roomba_carpetBoost", OFF)
            time.sleep(2)
            sendCommand("pIndoor_Roomba_vacHigh", OFF)
        elif state == "auto":
            sendCommand("pIndoor_Roomba_carpetBoost", ON)
            time.sleep(2)
            sendCommand("pIndoor_Roomba_vacHigh", OFF)
        elif state == "performance":
            sendCommand("pIndoor_Roomba_carpetBoost", OFF)
            time.sleep(2)
            sendCommand("pIndoor_Roomba_vacHigh", ON)


@rule("roboter_roomba.py")
class RoombaPassesControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pIndoor_Roomba_passes")]

    def execute(self, module, input):
        state = getItemState("pIndoor_Roomba_passes").toString()

        if state == "auto":
            sendCommand("pIndoor_Roomba_noAutoPasses", OFF)
            time.sleep(2)
            sendCommand("pIndoor_Roomba_twoPass", OFF)
        elif state == "one":
            sendCommand("pIndoor_Roomba_noAutoPasses", ON)
            time.sleep(2)
            sendCommand("pIndoor_Roomba_twoPass", OFF)
        elif state == "two":
            sendCommand("pIndoor_Roomba_noAutoPasses", OFF)
            time.sleep(2)
            sendCommand("pIndoor_Roomba_twoPass", ON)


@rule("roboter_roomba.py")
class RoombaLastUpdateTimestampRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 2,17,32,47 * * * ?"),
            ItemStateChangeTrigger("pIndoor_Roomba_online"),
            ItemStateChangeTrigger("pIndoor_Roomba_status")
        ]

    def execute(self, module, input):
        msg = ""
        cleaning_state = OFF

        if getItemState("pIndoor_Roomba_online") == OFF:
            msg = "Offline"
        else:
            status = getItemState("pIndoor_Roomba_status").toString()

            if status == "Running":
                msg = "Reinigt"
                cleaning_state = ON
            elif status == "Charging":
                msg = "In Ladestation"
            elif status == "Stuck":
                msg = u"Hängt fest"
            else:
                msg = status

        postUpdateIfChanged("pIndoor_Roomba_StatusFormatted", msg)

        postUpdateIfChanged("pIndoor_Roomba_cleaning_state", cleaning_state)


@rule("roboter_roomba.py")
class RoombaErrorRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pIndoor_Roomba_error")]

    def execute(self, module, input):
        if getItemState("pIndoor_Roomba_error") == ON:
            postUpdate("pIndoor_Roomba_errorFormatted", getItemState("pIndoor_Roomba_errortext").toString())
        else:
            postUpdate("pIndoor_Roomba_errorFormatted", "Alles OK")


@rule("roboter_roomba.py")
class RoombaCleanedAreaRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pIndoor_Roomba_sqft")]

    def execute(self, module, input):
        postUpdate("pIndoor_Roomba_sqm", u"{}".format( round(getItemState("pIndoor_Roomba_sqft").doubleValue() / 10.76391041671) ))


@rule("roboter_roomba.py")
class RoombaUpdateCommandRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pIndoor_Roomba_phase")]

    def execute(self, module, input):
        state = getItemState("pIndoor_Roomba_phase").toString()
        if state == "run":
            postUpdate("pIndoor_Roomba_command", "start")
        elif state == "hmUsrDock":
            postUpdate("pIndoor_Roomba_command", "pause")
        elif state == "hmMidMsn":
            postUpdate("pIndoor_Roomba_command", "pause")
        elif state == "hmPostMsn":
            postUpdate("pIndoor_Roomba_command", "dock")
        elif state == "charge":
            postUpdate("pIndoor_Roomba_command", "dock")
        elif state == "stop":
            postUpdate("pIndoor_Roomba_command", "stop")
        elif state == "pause":
            postUpdate("pIndoor_Roomba_command", "pause")
        elif state == "stuck":
            postUpdate("pIndoor_Roomba_command", "stop")


@rule("roboter_roomba.py")
class RoombaBinFullNotificationRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pIndoor_Roomba_full", state="ON")]

    def execute(self, module, input):
        sendNotification("Roomba", u"Behälter ist voll")


@rule("roboter_roomba.py")
class RoombaErrorNotificationRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pIndoor_Roomba_error", state="ON")]

    def execute(self, module, input):
        sendNotification("Roomba", u"Es ist ein Fehler aufgetreten")


@rule("roboter_roomba.py")
class RoombaNotificationRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pIndoor_Roomba_StatusFormatted")]

    def execute(self, module, input):
        sendNotification("Roomba", getItemState("pIndoor_Roomba_StatusFormatted").toString())


@rule("roboter_roomba.py")
class RoombaAutomaticRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 2,17,32,47 8-15 ? * MON-FRI")]

    def execute(self, module, input):
        if getItemState("pOther_Presence_State").intValue() == PresenceHelper.STATE_AWAY and itemLastChangeOlderThen("pOther_Presence_State", ZonedDateTime.now().minusMinutes(60)) \
                and getItemState("pIndoor_Roomba_auto") == ON \
                and getItemState("pIndoor_Roomba_status").toString() == "Charging" \
                and getItemState("pIndoor_Roomba_batPct").intValue() >= 100 \
                and getItemState("pIndoor_Roomba_error") == OFF \
                and getItemState("pIndoor_Roomba_full") == OFF \
                and itemLastChangeOlderThen("pIndoor_Roomba_cleaning_state", ZonedDateTime.now().minusMinutes(360)):
            sendCommand("pIndoor_Roomba_command", "start")
