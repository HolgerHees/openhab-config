from shared.triggers import ItemStateUpdateTrigger, CronTrigger

from shared.helper import rule, postUpdate

from shared.semantic.command_processor import CommandProcessor

from alexa_device_config import AlexaDevices
 
from custom.semantic_test import Cases
from custom.alexa import AlexaHelper
from custom.shuffle import ShuffleHelper

import traceback


class Tests:
    @staticmethod
    def process(processor,log,ir):
        for case in Cases['enabled']:
            if "client_id" in case:
                voice_command, client_id = processor.parseData(u"{}|{}".format(case['phrase'],case['client_id']))
            else:
                voice_command, client_id = processor.parseData(case['phrase'])

            fallback_location_name = AlexaHelper.getLocationByDeviceId(client_id)

            try:
                actions = processor.process(voice_command, fallback_location_name)

                msg, is_valid = processor.applyActions(actions,voice_command,True)
            except:
                log.info(traceback.format_exc())
                raise Exception()

            item_actions_skipped = []
            for action in actions:
                for item_action in action.item_actions:
                    item_actions_skipped.append(item_action)

            case_actions_excpected = []
            item_actions_applied = []
            for case_action in case["items"]:
                case_actions_excpected.append(case_action)
                case_item = case_action[0]
                case_cmd = case_action[1]
                for action in actions:
                    for item_action in action.item_actions:
                        if item_action in item_actions_applied:
                            continue
                        if item_action.item.getName() == case_item and item_action.cmd_value == case_cmd:
                            item_actions_applied.append(item_action)
                            item_actions_skipped.remove(item_action)
                            case_actions_excpected.remove(case_action)

            excpected_result = case["is_valid"] == is_valid if "is_valid" in case else is_valid
      
            if excpected_result \
                and len(item_actions_skipped) == 0 and len(item_actions_applied) == len(case["items"]):
                log.info(u"OK  - Input: '{}' - MSG: '{}'".format(voice_command,msg))
            else:
                log.info(u"ERR - Input: '{}' - MSG: '{}'".format(voice_command,msg))
                for case_action in case_actions_excpected:
                    log.info(u"       MISSING     => {} => {}".format(case_action[0],case_action[1]))
                for item_action in item_actions_skipped:
                    log.info(u"       UNEXCPECTED => {} => {}".format(item_action.item.getName(),item_action.cmd_value))
                for item_action in item_actions_applied:
                    log.info(u"       MATCH       => {} => {}".format(item_action.item.getName(),item_action.cmd_value))
 
                items = []
                for item_action in item_actions_skipped:
                    items.append(u"[\"{}\",\"{}\"]".format(item_action.item.getName(),item_action.cmd_value))
                for item_action in item_actions_applied:
                    items.append(u"[\"{}\",\"{}\"]".format(item_action.item.getName(),item_action.cmd_value))
                msg = u"[{}]".format(",".join(items))
 
                log.info(u"\n\n{}\n\n".format(msg))
                raise Exception("Wrong detection")
 
@rule("voice_command.py")
class VoiceCommandRule:
    def __init__(self):
        self.triggers = [ 
            ItemStateUpdateTrigger("VoiceCommand"),
            CronTrigger("0 0 0 * * ?")
            #ItemEventTrigger(["ItemAddedEvent","ItemRemovedEvent","ItemUpdatedEvent"])
        ]
        self.processor = CommandProcessor(self.log,ir)
        Tests.process(self.processor,self.log,ir)

    def execute(self, module, input):       
        if 'event' not in input:
            self.processor = CommandProcessor(self.log,ir)
            Tests.process(self.processor,self.log,ir)
            #self.log.info(u"{}".format(input))
        else:
            postUpdate("VoiceMessage","")

            voice_command, client_id = self.processor.parseData(input['event'].getItemState().toString())
            fallback_location_name = AlexaHelper.getLocationByDeviceId(client_id)

            self.log.info(u"Process: '{}', Location: '{}'".format(voice_command, client_id if fallback_location_name is None else fallback_location_name))

            actions = self.processor.process(voice_command, fallback_location_name)

            msg, is_valid = self.processor.applyActions(actions,voice_command,False)

            msg = ShuffleHelper.getRandomSynonym(msg)

            postUpdate("VoiceMessage",msg)

#postUpdate("VoiceCommand","Flur farbe grün")

