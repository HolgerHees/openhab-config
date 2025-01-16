from openhab import Registry

from shared.notification import NotificationHelper

from configuration import customConfigs


class AlexaHelper:
    EFFECT_WISPER = 1

    #@staticmethod
    #def _getMessageDeviceItemByLocation(location):
    #    return "{}_Message".format(customConfigs["alexa_location_device_map"][location])

    #@staticmethod
    #def sendMessageToLocation(location, message):
    #    Registry.getItem(AlexaHelper._getMessageDeviceItemByLocation(location)).sendCommand(message)

    @staticmethod
    def getLocationByDeviceId(client_id):
        return customConfigs["alexa_devices"][client_id] if client_id in customConfigs["alexa_devices"] else None

    @staticmethod
    def _getTTSDeviceItemByLocation(location):
        return "{}_TTS".format(customConfigs["alexa_location_device_map"][location])

    @staticmethod
    def sendTTS(message, header = None, location = None, priority = NotificationHelper.PRIORITY_INFO, effects = 0 ):
        is_announcement = location is None

        if header is not None:
            raw_msg = "{} {}".format(header, message)
            message = "{}. {}".format(header, message) if is_announcement else "{}<break time=\"1s\"/>{}".format(header, message)
        else:
            raw_msg = message

        Registry.getItem("Alexa_Last_TTS").postUpdate(raw_msg)

        #message = message.replace("ö","oe").replace("ü","ue").replace("ä","ae").replace("ß","ss")

        if not is_announcement and effects & AlexaHelper.EFFECT_WISPER:
            message = "<amazon:effect name=\"whispered\">{}</amazon:effect>".format(message)

        if location is None:
            Registry.getItem("pGF_Livingroom_Alexa_CMD").sendCommand("Mache eine Ankündigung. {}".format(message))
        else:
            if priority == NotificationHelper.PRIORITY_ALERT:
                Registry.getItem(AlexaHelper._getTTSDeviceItemByLocation(location)).sendCommand("<speak>Alarm <audio src=\"soundbank://soundlibrary/scifi/amzn_sfx_scifi_alarm_06\"/> {}</speak>".format(message))
            else:
                Registry.getItem(AlexaHelper._getTTSDeviceItemByLocation(location)).sendCommand("<speak>{}</speak>".format(message))
