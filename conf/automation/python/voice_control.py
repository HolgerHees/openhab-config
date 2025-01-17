from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateUpdateTrigger

from shared.semantic.command_processor import CommandProcessor

from custom.semantic_test import Cases
from custom.alexa import AlexaHelper
from custom.shuffle import ShuffleHelper


@rule(
    triggers = [
        GenericCronTrigger("0 0 0 * * ?"),
        ItemStateUpdateTrigger("VoiceCommand")
    ]
)
class Main:
    def __init__(self):
        self.processor = CommandProcessor(ir)
        #self.test(ir)

    def execute(self, module, input):
        if input['event'].getType() == "TimerEvent":
            self.processor = CommandProcessor(ir)
            self.test(ir)
            #self.logger.info("{}".format(input))
        else:
            Registry.getItem("VoiceMessage").postUpdate("")

            voice_command, client_id = self.processor.parseData(input['event'].getItemState().toString())
            fallback_location_name = AlexaHelper.getLocationByDeviceId(client_id)

            self.logger.info("Process: '{}', Location: '{}'".format(voice_command, client_id if fallback_location_name is None else fallback_location_name))

            actions = self.processor.process(voice_command, fallback_location_name)

            #for action in actions:
            #    for item_action in action.item_actions:
            #        self.logger.info("{} {}".format(item_action.item,item_action.cmd_value))

            msg, is_valid = self.processor.applyActions(actions,voice_command,False)

            msg = ShuffleHelper.getRandomSynonym(msg)

            Registry.getItem("VoiceMessage").postUpdate(msg)

    def test(self,ir):
        for case in Cases['enabled']:
            if "client_id" in case:
                voice_command, client_id = self.processor.parseData("{}|{}".format(case['phrase'],case['client_id']))
            else:
                voice_command, client_id = self.processor.parseData(case['phrase'])

            fallback_location_name = AlexaHelper.getLocationByDeviceId(client_id)

            actions = self.processor.process(voice_command, fallback_location_name)

            msg, is_valid = self.processor.applyActions(actions,voice_command,True)

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
                self.logger.info("OK  - Input: '{}' - MSG: '{}'".format(voice_command,msg))
            else:
                self.logger.info("ERR - Input: '{}' - MSG: '{}'".format(voice_command,msg))
                for case_action in case_actions_excpected:
                    self.logger.info("       MISSING     => {} => {}".format(case_action[0],case_action[1]))
                for item_action in item_actions_skipped:
                    self.logger.info("       UNEXCPECTED => {} => {}".format(item_action.item.getName(),item_action.cmd_value))
                for item_action in item_actions_applied:
                    self.logger.info("       MATCH       => {} => {}".format(item_action.item.getName(),item_action.cmd_value))

                items = []
                for item_action in item_actions_skipped:
                    items.append("[\"{}\",\"{}\"]".format(item_action.item.getName(),item_action.cmd_value))
                for item_action in item_actions_applied:
                    items.append("[\"{}\",\"{}\"]".format(item_action.item.getName(),item_action.cmd_value))
                msg = "[{}]".format(",".join(items))

                self.logger.info("\n\n{}\n\n".format(msg))
                raise Exception("Wrong detection")
