from marvin.helper import rule, sendNotification, getItemState, postUpdateIfChanged
from core.triggers import CronTrigger, ItemStateChangeTrigger

@rule("roboter_messages.py")
class RoboterMessagesRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("roomba_status"),
            ItemStateChangeTrigger("roomba_full"),
            ItemStateChangeTrigger("MowerStatus")
        ]

    def execute(self, module, input):
        group = "Fehler"
        active = []

        if getItemState("roomba_status").toString() == "Stuck" or getItemState("roomba_full") == ON:
            active.append("Roomba")

        if getItemState("MowerStatus").intValue() == 7:
            active.append("Mower")

        if len(active) == 0:
            active.append("Alles normal")
            group = "Info"

        msg = ", ".join(active)

        if postUpdateIfChanged("RoboterStatus", msg):
            sendNotification("Roboter " + group, msg)

