from alexa_device_config import AlexaDevices
from alexa_device_config import AlexaLocationDeviceMap

from shared.helper import sendCommand

class AlexaHelper:
    @staticmethod
    def getLocationByDeviceId(client_id):
        return AlexaDevices[client_id] if client_id in AlexaDevices else None

    @staticmethod
    def _getTTSDeviceItemByLocationItem(location_item):
        return "{}_TTS".format(AlexaLocationDeviceMap[location_item])

    @staticmethod
    def sendTTSToLocation(location_item, message):
        sendCommand(AlexaHelper._getTTSDeviceItemByLocationItem(location_item), message)

    @staticmethod
    def sendAlarmTTSToLocation(location_item, message):
        sendCommand(AlexaHelper._getTTSDeviceItemByLocationItem(location_item), "<speak>Alarm <audio src=\"soundbank://soundlibrary/scifi/amzn_sfx_scifi_alarm_06\"/> {}</speak>".format(message))

    #@staticmethod
    #def _getAlarmDeviceItemByLocationItem(location_item):
    #    return "{}_AlarmSound".format(AlexaLocationDeviceMap[location_item])
