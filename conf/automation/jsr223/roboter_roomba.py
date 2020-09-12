import time

from custom.helper import rule, getNow, itemLastChangeOlderThen, getItemState, sendNotification, postUpdate, postUpdateIfChanged, sendCommand
from core.triggers import CronTrigger, ItemStateChangeTrigger


@rule("roboter_roomba.py")
class RoombaBoostControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("roomba_boost")]

    def execute(self, module, input):
        state = getItemState("roomba_boost").toString()

        if state == "eco":
            sendCommand("roomba_carpetBoost", OFF)
            time.sleep(2)
            sendCommand("roomba_vacHigh", OFF)
        elif state == "auto":
            sendCommand("roomba_carpetBoost", ON)
            time.sleep(2)
            sendCommand("roomba_vacHigh", OFF)
        elif state == "performance":
            sendCommand("roomba_carpetBoost", OFF)
            time.sleep(2)
            sendCommand("roomba_vacHigh", ON)


@rule("roboter_roomba.py")
class RoombaPassesControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("roomba_passes")]

    def execute(self, module, input):
        state = getItemState("roomba_passes").toString()

        if state == "auto":
            sendCommand("roomba_noAutoPasses", OFF)
            time.sleep(2)
            sendCommand("roomba_twoPass", OFF)
        elif state == "one":
            sendCommand("roomba_noAutoPasses", ON)
            time.sleep(2)
            sendCommand("roomba_twoPass", OFF)
        elif state == "two":
            sendCommand("roomba_noAutoPasses", OFF)
            time.sleep(2)
            sendCommand("roomba_twoPass", ON)


@rule("roboter_roomba.py")
class RoombaLastUpdateTimestampRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 2,17,32,47 * * * ?"),
            ItemStateChangeTrigger("roomba_online"),
            ItemStateChangeTrigger("roomba_status")
        ]

    def execute(self, module, input):
        msg = ""
        cleaning_state = OFF

        if getItemState("roomba_online") == OFF:
            msg = "Offline"
        else:
            status = getItemState("roomba_status").toString()

            if status == "Running":
                msg = "Reinigt"
                cleaning_state = ON
            elif status == "Charging":
                msg = "In Ladestation"
            elif status == "Stuck":
                msg = u"Hängt fest"
            else:
                msg = status

        postUpdateIfChanged("roomba_StatusFormatted", msg)

        postUpdateIfChanged("roomba_cleaning_state", cleaning_state)


@rule("roboter_roomba.py")
class RoombaErrorRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("roomba_error")]

    def execute(self, module, input):
        if getItemState("roomba_error") == ON:
            postUpdate("roomba_errorFormatted", getItemState("roomba_errortext").toString())
        else:
            postUpdate("roomba_errorFormatted", "Alles OK")


@rule("roboter_roomba.py")
class RoombaCleanedAreaRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("roomba_sqft")]

    def execute(self, module, input):
        postUpdate("roomba_sqm", u"{}".format( round(getItemState("roomba_sqft").doubleValue() / 10.76391041671) ))


@rule("roboter_roomba.py")
class RoombaUpdateCommandRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("roomba_phase")]

    def execute(self, module, input):
        state = getItemState("roomba_phase").toString()
        if state == "run":
            postUpdate("roomba_command", "start")
        elif state == "hmUsrDock":
            postUpdate("roomba_command", "pause")
        elif state == "hmMidMsn":
            postUpdate("roomba_command", "pause")
        elif state == "hmPostMsn":
            postUpdate("roomba_command", "dock")
        elif state == "charge":
            postUpdate("roomba_command", "dock")
        elif state == "stop":
            postUpdate("roomba_command", "stop")
        elif state == "pause":
            postUpdate("roomba_command", "pause")
        elif state == "stuck":
            postUpdate("roomba_command", "stop")


@rule("roboter_roomba.py")
class RoombaBinFullNotificationRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("roomba_full", state="ON")]

    def execute(self, module, input):
        sendNotification("Roomba", u"Behälter ist voll")


@rule("roboter_roomba.py")
class RoombaErrorNotificationRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("roomba_error", state="ON")]

    def execute(self, module, input):
        sendNotification("Roomba", u"Es ist ein Fehler aufgetreten")


@rule("roboter_roomba.py")
class RoombaNotificationRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("roomba_StatusFormatted")]

    def execute(self, module, input):
        sendNotification("Roomba", getItemState("roomba_StatusFormatted").toString())


@rule("roboter_roomba.py")
class RoombaAutomaticRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 2,17,32,47 8-15 ? * MON-FRI")]

    def execute(self, module, input):
        if getItemState("State_Presence").intValue() == 0 \
                and getItemState("roomba_auto") == ON \
                and getItemState("roomba_status").toString() == "Charging" \
                and getItemState("roomba_batPct").intValue() >= 100 \
                and getItemState("roomba_error") == OFF \
                and getItemState("roomba_full") == OFF:
            if itemLastChangeOlderThen("roomba_cleaning_state", getNow().minusMinutes(360)) \
                    and itemLastChangeOlderThen("State_Presence", getNow().minusMinutes(60)):
                sendCommand("roomba_command", "start")
