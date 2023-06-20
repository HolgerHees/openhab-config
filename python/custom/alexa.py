# -*- coding: utf-8 -*-

from alexa_device_config import AlexaDevices
from alexa_device_config import AlexaLocationDeviceMap

from shared.helper import sendCommand, postUpdate, NotificationHelper

class AlexaHelper:
    EFFECT_WISPER = 1

    @staticmethod
    def getLocationByDeviceId(client_id):
        return AlexaDevices[client_id] if client_id in AlexaDevices else None

    #@staticmethod
    #def _getMessageDeviceItemByLocation(location):
        return "{}_Message".format(AlexaLocationDeviceMap[location])

    #@staticmethod
    #def sendMessageToLocation(location, message):
    #    sendCommand(AlexaHelper._getMessageDeviceItemByLocation(location), message)

    @staticmethod
    def _getTTSDeviceItemByLocation(location):
        return "{}_TTS".format(AlexaLocationDeviceMap[location])

    @staticmethod
    def sendTTS(message, header = None, location = None, priority = NotificationHelper.PRIORITY_INFO, effects = 0 ):
        if header is not None:
            raw_msg = "{} {}".format(header, message)
            message = "{}<break time=\"1s\"/>{}".format(header, message)
        else:
            raw_msg = message

        postUpdate("Alexa_Last_TTS", raw_msg)

        message = message.replace(u"ö","oe").replace(u"ü","ue").replace(u"ä","ae").replace(u"ß","ss")

        if effects & AlexaHelper.EFFECT_WISPER:
            message = u"<amazon:effect name=\"whispered\">{}</amazon:effect>".format(message)

        if location is None:
            sendCommand("pGF_Livingroom_Alexa_CMD", u"Mache eine Ankuendigung. {}".format(message))
        else:
            if priority == NotificationHelper.PRIORITY_ALERT:
                sendCommand(AlexaHelper._getTTSDeviceItemByLocation(location), u"<speak>Alarm <audio src=\"soundbank://soundlibrary/scifi/amzn_sfx_scifi_alarm_06\"/> {}</speak>".format(message))
            else:
                sendCommand(AlexaHelper._getTTSDeviceItemByLocation(location), u"<speak>{}</speak>".format(message))

    #@staticmethod
    #def _getAlarmDeviceItemByLocation(location):
    #    return "{}_AlarmSound".format(AlexaLocationDeviceMap[location])
