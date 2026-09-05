from openhab import rule, Registry, logger
from openhab.triggers import GenericCronTrigger, ItemStateUpdateTrigger

from shared.semantic.command_processor import CommandProcessor

from custom.semantic_test import Cases
from custom.voice import VoiceAssistentHelper
#from custom.shuffle import ShuffleHelper

from openhab.actions import Voice

import scope


@rule(
    triggers = [
#        GenericCronTrigger("0 0 0 * * ?"),
        ItemStateUpdateTrigger("pOther_SmartSpeaker_VoiceCommand")
    ]
)
class MainSmartSpeaker:
    def execute(self, module, input):
        self.logger.info(str(input))
        self.logger.info(str(module))

#startDialog(String ks, String stt, String tts, String voice, String interpreters, String source, String sink, String locale, String keyword, String listeningItem)
#Voice.startDialog("esphome:device:home-speaker-1:source:voice_assistant", "enhancedjavasound")

#Voice.stopDialog("esphome:device:home-speaker-1:source:voice_assistant")
#Voice.startDialog("rustpotterks", "whisperstt", "openaitts", "openaitts:jarvis", "rulehli", "esphome:device:home-speaker-1:source:voice_assistant", "esphome:device:home-speaker-1:sink:", "de-DE", "Hey Marvin", "pOther_SmartSpeaker_VoiceCommand")



#Voice.startDialog("rustpotterks", "voskstt", "pipertts", "pipertts:kerstin-low-de_DE", "rulehli", "esphome:device:home-speaker-1:source:voice_assistant", "esphome:device:home-speaker-1:sink:", "de-DE", "Hey Jarvis", "pOther_SmartSpeaker_VoiceCommand")
#Voice.stopDialog("esphome:device:home-speaker-1:source:voice_assistant")


#Voice.listenAndAnswer("esphome:device:home-speaker-1:source:voice_assistant", "enhancedjavasound")



@rule(
    triggers = [
#        GenericCronTrigger("0 0 0 * * ?"),
        ItemStateUpdateTrigger("VoiceCommand")
    ]
)
class MainAlexa:
    def execute(self, module, input):
        Registry.getItem("VoiceMessage").postUpdate("")

        location_name = client_id = None
        message = input['event'].getItemState().toString()
        if "|" in message:
            message, client_id = message.split("|")
            location_name = VoiceAssistentHelper.getLocationByDeviceId(client_id.replace("amzn1.ask.device.", ""))

        self.logger.info("Process: '{}', Location: '{}'".format(message, client_id if location_name is None else location_name))

        if "gute nacht" in message.lower():
            message = "Schalte Scene 4 ein und antworte mit einem zufälligem synonym für 'Schlaf schön'"
        elif location_name is not None:
            location_item = Registry.getItem(location_name)
            message = "{}. Falls in der Frage kein Ort angegeben wurde, er im Context aber Sinn ergeben würde, dann nehme an der Ort ist {}".format(message, location_item.getLabel())

        response = VoiceAssistentHelper.sendMessage(message, True)

        self.logger.info("Answer: '{}'".format(response))

        Registry.getItem("VoiceMessage").postUpdate(response)
