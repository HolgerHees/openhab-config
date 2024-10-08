# -*- coding: utf-8 -*-

from configuration import customConfigs

from shared.helper import sendCommand, postUpdate, NotificationHelper

class AlexaHelper:
    EFFECT_WISPER = 1

    @staticmethod
    def getLocationByDeviceId(client_id):
        return customConfigs["alexa_devices"][client_id] if client_id in customConfigs["alexa_devices"] else None

    #@staticmethod
    #def _getMessageDeviceItemByLocation(location):
        return "{}_Message".format(customConfigs["alexa_location_device_map"][location])

    #@staticmethod
    #def sendMessageToLocation(location, message):
    #    sendCommand(AlexaHelper._getMessageDeviceItemByLocation(location), message)

    @staticmethod
    def _getTTSDeviceItemByLocation(location):
        return "{}_TTS".format(customConfigs["alexa_location_device_map"][location])

    @staticmethod
    def sendTTS(message, header = None, location = None, priority = NotificationHelper.PRIORITY_INFO, effects = 0 ):
        is_announcement = location is None

        if header is not None:
            raw_msg = u"{} {}".format(header, message)
            message = u"{}. {}".format(header, message) if is_announcement else u"{}<break time=\"1s\"/>{}".format(header, message)
        else:
            raw_msg = message

        postUpdate("Alexa_Last_TTS", raw_msg)

        #message = message.replace(u"ö",u"oe").replace(u"ü",u"ue").replace(u"ä",u"ae").replace(u"ß",u"ss")

        if not is_announcement and effects & AlexaHelper.EFFECT_WISPER:
            message = u"<amazon:effect name=\"whispered\">{}</amazon:effect>".format(message)

        if location is None:
            sendCommand("pGF_Livingroom_Alexa_CMD", u"Mache eine Ankündigung. {}".format(message))
        else:
            if priority == NotificationHelper.PRIORITY_ALERT:
                sendCommand(AlexaHelper._getTTSDeviceItemByLocation(location), u"<speak>Alarm <audio src=\"soundbank://soundlibrary/scifi/amzn_sfx_scifi_alarm_06\"/> {}</speak>".format(message))
            else:
                sendCommand(AlexaHelper._getTTSDeviceItemByLocation(location), u"<speak>{}</speak>".format(message))

    #@staticmethod
    #def _getAlarmDeviceItemByLocation(location):
    #    return "{}_AlarmSound".format(customConfigs["alexa_location_device_map"][location])
