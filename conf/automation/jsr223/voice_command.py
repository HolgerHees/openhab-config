from core.triggers import ItemStateUpdateTrigger

from shared.helper import rule, postUpdate

from shared.semantic.model.semantic_test import Cases

from shared.semantic.command_processor import CommandProcessor

from alexa_device_config import AlexaDevices

import traceback
       
@rule("voice_command.py")
class VoiceCommandRule:
    def __init__(self):
        self.triggers = [ ItemStateUpdateTrigger("VoiceCommand") ]
        self.processor = CommandProcessor(self.log,ir)

    def execute(self, module, input):
        postUpdate("VoiceMessage","")

        voice_command, client_id = self.processor.parseData(input['event'].getItemState().toString())
        fallback_location_name = AlexaDevices[client_id] if client_id in AlexaDevices else None

        self.log.info(u"Process: '{}', Location: '{}'".format(voice_command, fallback_location_name))

        actions = self.processor.process(voice_command, fallback_location_name)

        msg, is_valid = self.processor.applyActions(actions,voice_command,False)

        postUpdate("VoiceMessage",msg)
                                           
#postUpdate("VoiceCommand","Flur farbe grün")

@rule("voice_command.py")
class TestRule:
    def __init__(self):
        voice_command_rule = CommandProcessor(self.log,ir)
        for case in Cases['enabled']:
            if "client_id" in case:
                voice_command, client_id = voice_command_rule.parseData(u"{}|{}".format(case['phrase'],case['client_id']))
            else:
                voice_command, client_id = voice_command_rule.parseData(case['phrase'])

            fallback_location_name = AlexaDevices[client_id] if client_id in AlexaDevices else None

            try:
                actions = voice_command_rule.process(voice_command, fallback_location_name)

                msg, is_valid = voice_command_rule.applyActions(actions,voice_command,True)
            except:
                self.log.info(traceback.format_exc())
                raise Exception()

            item_actions_skipped = []
            location_names = []
            for action in actions:
                location_names += map(lambda location: location.getItem().getName(),action.locations)
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
    
            location_names = list(set(location_names))
            if len(location_names) > 0 and case.get("location_count",1) != len(location_names):
                excpected_result = False
                 
            if excpected_result \
                and len(item_actions_skipped) == 0 and len(item_actions_applied) == len(case["items"]):
                self.log.info(u"OK  - Input: '{}' - MSG: '{}'".format(voice_command,msg))
            else:
                self.log.info(u"ERR - Input: '{}' - MSG: '{}'".format(voice_command,msg))
                for action in actions:
                    for location in action.locations:
                        self.log.info(u"       LOCATION:   => {}".format(location.getItem().getName()))
                for case_action in case_actions_excpected:
                    self.log.info(u"       MISSING     => {} => {}".format(case_action[0],case_action[1]))
                for item_action in item_actions_skipped:
                    self.log.info(u"       UNEXCPECTED => {} => {}".format(item_action.item.getName(),item_action.cmd_value))
                for item_action in item_actions_applied:
                    self.log.info(u"       MATCH       => {} => {}".format(item_action.item.getName(),item_action.cmd_value))
 
                items = []
                for item_action in item_actions_skipped:
                    items.append(u"[\"{}\",\"{}\"]".format(item_action.item.getName(),item_action.cmd_value))
                for item_action in item_actions_applied:
                    items.append(u"[\"{}\",\"{}\"]".format(item_action.item.getName(),item_action.cmd_value))
                msg = u"[{}]".format(",".join(items))
                if len(location_names) > 1:
                    msg = u"{}, \"location_count\": {}".format(msg,len(location_names))
 
                self.log.info(u"\n\n{}\n\n".format(msg))
                raise Exception("Wrong detection")
     
    def execute(self, module, input):
        pass      