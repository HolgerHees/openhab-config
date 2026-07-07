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
        ItemStateUpdateTrigger("VoiceCommand")
    ]
)
class MainNew:
    def execute(self, module, input):
        Registry.getItem("VoiceMessage").postUpdate("")

        location_name = client_id = None
        message = input['event'].getItemState().toString()
        if "|" in message:
            message, client_id = message.split("|")
            location_name = VoiceAssistentHelper.getLocationByDeviceId(client_id)

        self.logger.info("Process: '{}', Location: '{}'".format(message, client_id if location_name is None else location_name))

        response = VoiceAssistentHelper.sendMessage(message, True)

        self.logger.info("Answer: '{}'".format(response))

        Registry.getItem("VoiceMessage").postUpdate(response)
