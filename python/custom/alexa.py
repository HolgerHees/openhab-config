from alexa_device_config import AlexaDevices
from alexa_device_config import AlexaLocationDeviceMap

from shared.helper import sendCommand, postUpdate, NotificationHelper

class AlexaHelper:
    EFFECT_WISPER = 1

    @staticmethod
    def getLocationByDeviceId(client_id):
        return AlexaDevices[client_id] if client_id in AlexaDevices else None

    #@staticmethod
    #def _getMessageDeviceItemByLocationItem(location_item):
        return "{}_Message".format(AlexaLocationDeviceMap[location_item])

    #@staticmethod
    #def sendMessageToLocation(location_item, message):
    #    sendCommand(AlexaHelper._getMessageDeviceItemByLocationItem(location_item), message)

    @staticmethod
    def _getTTSDeviceItemByLocationItem(location_item):
        return "{}_TTS".format(AlexaLocationDeviceMap[location_item])

    @staticmethod
    def sendTTSToLocation(message, location_item = None, prioriy = NotificationHelper.PRIORITY_INFO, effects = None ):

        postUpdate("pIndoor_Alexa_Last_TTS", message)

        if effects & AlexaHelper.EFFECT_WISPER:
            message = "<amazon:effect name=\"whispered\">{}</amazon:effect>".format(message)

        if location_item is None:
            sendCommand("pGF_Livingroom_Alexa_CMD", "Ankuendigung, {}".format(message))
        else:
            if priority == NotificationHelper.PRIORITY_ALERT:
                sendCommand(AlexaHelper._getTTSDeviceItemByLocationItem(location_item), "<speak>Alarm <audio src=\"soundbank://soundlibrary/scifi/amzn_sfx_scifi_alarm_06\"/> {}</speak>".format(message))
            else:
                sendCommand(AlexaHelper._getTTSDeviceItemByLocationItem(location_item), "<speak>{}</speak>".format(message))

    #@staticmethod
    #def _getAlarmDeviceItemByLocationItem(location_item):
    #    return "{}_AlarmSound".format(AlexaLocationDeviceMap[location_item])
