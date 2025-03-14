import json

from openhab.actions import HTTP

from configuration import customConfigs

class FrigateHelper:
    def getLatestSnapshotUrl(camera_name):
        return "{}{}/latest.jpg?h=640".format(customConfigs['freegate_api'], camera_name)

    def getDetectionSnapshotUrl(event_id):
        return "{}events/{}/snapshot.jpg?bbox=1".format(customConfigs['freegate_api'], event_id)

    def createEvent(camera_name, label):
        url = "{}events/{}/{}/create".format(customConfigs['freegate_api'], camera_name, label)
        content = {
#          "source_type": "openhab",
          "sub_label": "openhab",
          "score": 0,
          "duration": 5,
          "include_recording": True,
          "draw": {}
        }
        HTTP.sendHttpPostRequest(url, "application/json", json.dumps(content))
