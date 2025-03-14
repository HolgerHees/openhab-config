from openhab import rule, Registry, logger
from openhab.triggers import ItemStateChangeTrigger, GenericCronTrigger, SystemStartlevelTrigger

from shared.notification import NotificationHelper

from custom.presence import PresenceHelper

from custom.frigate import FrigateHelper

from datetime import datetime
import json
import math


@rule(
    triggers = [
        #SystemStartlevelTrigger(80),
        GenericCronTrigger("0 0 0 * * ?"),
        ItemStateChangeTrigger("pOutdoor_Cameras_Reviews")
    ]
)
class Notification():
    def __init__(self):
        self.event_ids = {}
        self.camera_mapping = {
            "streedside": "an der Strasseseite",
            "toolshed": "im Garten"
        }

        self.event_mapping = {
            "alarm": ["Bewegung", "Bewegungsalarm", NotificationHelper.PRIORITY_NOTICE],
        #    "bell": ["Klingel (Openhab)", "Es klingelt jemand", NotificationHelper.PRIORITY_INFO],
        #    "motion": ["Bewegung (Openhab)", "Bewegungsinfo", NotificationHelper.PRIORITY_INFO]
        }

    def execute(self, module, input):
        if input['event'].getType() == "TimerEvent":
            now = datetime.now().astimezone()
            for event_id in list(self.event_ids.keys()):
                diff = (now - self.event_ids[event_id]["time"]).total_seconds()
                if ( self.event_ids[event_id]["type"] == "end" and diff > 300 ) or diff > 900:
                    del self.event_ids[event_id]
            return

        reviews = Registry.getItem("pOutdoor_Cameras_Reviews").getState()
        events = json.loads(reviews.toString())

        _payload = events["after"]

        event_id = _payload["id"]
        event_type = events["type"]

        if event_id in self.event_ids:
            self.event_ids[event_id] = { "type": event_type, "time": datetime.now().astimezone() }
            return

        if event_type == "new":
            return

        event_severity = _payload["severity"]
        #if event_severity not in ["alert", "detection"]:
        if event_severity not in ["alert"]:
            return

        #if Registry.getItemState("pOther_Presence_State").intValue() not in [PresenceHelper.STATE_AWAY, STATE_MAYBE_PRESENT]:
        #    return

        self.event_ids[event_id] = { "type": event_type, "time": datetime.now().astimezone() }

        event_camera = _payload["camera"]
        #event_objects = _payload["data"]["objects"]
        event_detections = _payload["data"]["detections"]
        event_objects = _payload["data"]["objects"]

        event_type = "alarm"
        for event_object in event_objects:
            if "openhab" in event_object:
                event_type = event_object.split(":")[0]

        # some events like doorbell can be ignored, because they are already notified
        if event_type not in self.event_mapping:
            return

        headline, detail, priority = self.event_mapping[event_type]

        detection_index = math.ceil( len(event_detections) - 1 )

        msg = "{} {}".format(detail, self.camera_mapping[event_camera])
        NotificationHelper.sendNotificationToAllAdmins(priority, headline, msg, FrigateHelper.getDetectionSnapshotUrl(event_detections[detection_index]))
