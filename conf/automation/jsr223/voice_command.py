from shared.helper import rule, postUpdate, sendCommandIfChanged, getItemState

from core.triggers import ItemStateUpdateTrigger

from alexa.device_config import AlexaDevices

from alexa.semantic_config import SemanticConfig

from alexa.semantic_items import SemanticItems

from alexa.semantic_test import Cases

import re
 
class VoiceAction:
    def __init__(self,voice_cmd):
        self.voice_cmd_complete = voice_cmd
        self.voice_cmd_unprocessed = voice_cmd
        self.voice_cmd_without_location = voice_cmd
        self.locations = []
        self.points = []

        self.cmd = None
        
        self.item_actions = []

class ItemCommand:
    def __init__(self,cmd,types,argument):
        self.cmd = cmd
        self.types = types
        self.argument = argument

class ItemAction:
    def __init__(self,item,cmd_name,cmd_argument):
        self.item = item
        self.cmd_name = cmd_name
        self.cmd_argument = cmd_argument
 
@rule("voice_command.py")
class VoiceCommandRule:
    def __init__(self):
        self.triggers = [ ItemStateUpdateTrigger("VoiceCommand") ]
        self.semantic_items = SemanticItems(ir,SemanticConfig)
        self.full_phrase_map, self.full_phrase_terms = self.buildSearchMap(self.semantic_items.semantic_items[SemanticConfig["main"]["phrase_equipment"]].children)
 
    def buildSearchMap(self,items):
        search_map = {}
        for semantic_item in items:
            for search_term in semantic_item.search_terms:
                if search_term not in search_map:
                    search_map[search_term] = []
                search_map[search_term].append(semantic_item)
        search_terms = sorted(search_map, key=len, reverse=True)
        return search_map, search_terms

    def getItemsByType(self,parent,type):
        result = []
        if parent.item.getType() == "Group":
            #self.log.info(u" => {} {}".format(parent.getName(),parent.getType()))
            items = parent.item.getMembers()
            for item in items:
                semantic_item = self.semantic_items.semantic_items[item.getName()]
                #self.log.info(u" => {}".format(item.getName()))
                if semantic_item.type == type:
                    result.append(semantic_item)
                else:
                    result = result + self.getItemsByType(semantic_item,type)
        return result

    def _searchItems(self,items,unprocessed_search,recursive,full_match,items_to_skip,is_sub_search,security_counter = 0):
        security_counter = security_counter + 1
        if security_counter >= 10:
            raise Exception("_searchItems: security counter matched. more then 10 loops.")
        #self.log.info(u"_searchItems: {}".format(','.join([str(item.item.getName()) for item in items]) ))
        # check for matches in items
        matched_items = []
        matched_search = None
        search_map, search_terms = self.buildSearchMap(items)
        for search_term in search_terms:
            if not is_sub_search and search_term in SemanticConfig["main"]["phrase_sub"]:
                continue
    
            regex = self.semantic_items.semantic_search_full_regex[search_term] if full_match else self.semantic_items.semantic_search_part_regex[search_term]
            if regex.match(unprocessed_search):
                matched_items =  search_map[search_term]
                if len(items_to_skip) > 0:
                    matched_items = list(set(matched_items) - set(items_to_skip))
                if len(matched_items) > 0:
                    #self.log.info(u"matched_items: {} {}".format(search_term,','.join([str(item.item.getName()) for item in matched_items])))
                    matched_search = search_term
                    break
 
        if recursive:
            # collect items which does not match and collect their children of same type
            missing_items = list(set(items) - set(matched_items) - set(items_to_skip))
            #self.log.info(u"missing_items: {}".format(','.join([str(item.item.getName()) for item in missing_items]) ))
            to_check = []
            for item in missing_items:
                members = item.item.getMembers()
                for member in members:
                    semantic_member = self.semantic_items.semantic_items[member.getName()]
                    if member.getType() != "Group" or semantic_member.type != item.type:
                        continue
                    to_check.append(semantic_member)
        
            # check children for matches
            if len(to_check)>0:
                #self.log.info(u"to_check: {}".format(','.join([str(item.item.getName()) for item in to_check])))
                _matched_items, _matched_search, _unprocessed_search = self._searchItems(to_check,matched_search if matched_search is not None else unprocessed_search,recursive,full_match,items_to_skip,is_sub_search,security_counter)
                if matched_search == None:
                    unprocessed_search = _unprocessed_search
                    matched_search = _matched_search
                matched_items += _matched_items 
    
        if matched_search != None:
            unprocessed_search = unprocessed_search.replace(search_term,"")

        return matched_items, matched_search, unprocessed_search

    def searchItems(self,items,unprocessed_search,recursive,full_match,items_to_skip=[]):
        matched_items = []
        security_counter = 0
        while True:
            security_counter = security_counter + 1
            if security_counter >= 10:
                raise Exception(u"searchItems: security counter matched. more then 10 loops.")
            #self.log.info(u"search items")
            _items, _matched_search, _unprocessed_search = self._searchItems(items,unprocessed_search,recursive,full_match,items_to_skip,len(matched_items)>0)
            if len(_items) == 0:
                break
            matched_items = _items
            items = matched_items
            unprocessed_search = _unprocessed_search

        #self.log.info(u"found items: {}".format(','.join([str(item.item.getName()) for item in matched_items]) ))
        #raise Exception("test")
        return matched_items, unprocessed_search

    def detectLocations(self,actions):
        for action in actions:
            # search for locations
            matched_locations, unprocessed_search = self.searchItems(self.semantic_items.root_locations,action.voice_cmd_unprocessed,recursive=True,full_match=True)
            if len(matched_locations) == 0:
                matched_locations, unprocessed_search = self.searchItems(self.semantic_items.root_locations,action.voice_cmd_unprocessed,recursive=True,full_match=False)
            action.voice_cmd_unprocessed = unprocessed_search
            action.voice_cmd_without_location = unprocessed_search
            action.locations = matched_locations

    def fillLocationsFallbacks(self,actions,fallback_location_name):
        # Fill missing locations forward
        last_locations = []
        for action in actions:
            # if no location found use the last one
            if len(action.locations) == 0:
                action.locations = last_locations
            else:
                last_locations = action.locations
 
        # Fill missing locations backward
        last_locations = []
        for action in reversed(actions):
            if len(action.locations) == 0:
                action.locations = last_locations
            else:
                last_locations = action.locations

        # Fill missing locations with fallbacks
        if fallback_location_name != None:
            for action in actions:
                if len(action.locations) != 0:
                    continue
                action.locations = [ self.semantic_items.semantic_items[fallback_location_name] ]

    def checkPoints(self,action,unprocessed_search,items_to_skip):
        #self.log.info(u"checkPoints")
        equipments = []
        for location in action.locations:
            # search for equipments    
            #self.log.info(u"  location: '{}', unprocessed_search: '{}'".format(location,unprocessed_search))
            equipments += self.getItemsByType(location,"Equipment")

        matched_equipments, unprocessed_search = self.searchItems(equipments,unprocessed_search,recursive=True,full_match=False,items_to_skip=items_to_skip)
 
        # check points of equipments 
        if len(matched_equipments) > 0:
            points = []
            #point_matches = False
            #processed_search_terms = []
            for equipment in matched_equipments:
                #self.log.info(u"  equipment: '{}', unprocessed_search: '{}'".format(equipment.item.getName(),unprocessed_search))
                points += self.getItemsByType(equipment,"Point")

            matched_points, unprocessed_search = self.searchItems(points,unprocessed_search,recursive=False,full_match=False,items_to_skip=items_to_skip)

            # add matched points or all equipment points if there are no matches
            action.points = points if len(matched_points) == 0 else matched_points
            return unprocessed_search

        # check points of locations
        points = []
        for location in action.locations:
            points += self.getItemsByType(location,"Point")

        matched_points, unprocessed_search = self.searchItems(points,unprocessed_search,recursive=False,full_match=False,items_to_skip=items_to_skip)
        action.points = matched_points

        return unprocessed_search 
 
    def detectPoints(self,actions):
        for action in actions:
            # search for points based on voice_cmd
            voice_cmd_unprocessed = self.checkPoints(action,action.voice_cmd_unprocessed,[])
            if voice_cmd_unprocessed != None:
                #self.log.info(voice_cmd_unprocessed)
                action.voice_cmd_unprocessed = voice_cmd_unprocessed

    def fillPointFallbacks(self,actions):
        # Fill missing points backward until command is found
        last_action = None
        for action in reversed(actions):
            if len(action.points) == 0:
                if last_action != None:
                    self.checkPoints(action,u"{} {}".format(last_action.voice_cmd_without_location,action.voice_cmd_unprocessed),last_action.points)
            else:
                last_action = action

            #if action.cmd != None:
            #    last_action = None
 
        # Fill missing points forwards
        last_action = None
        for action in actions:
            # if no points where found search again based on the last cmd with points
            if len(action.points) == 0:
                if last_action != None:
                    #self.log.info(u"fallback {}".format(last_action.voice_cmd_without_location))
                    self.checkPoints(action,u"{} {}".format(last_action.voice_cmd_without_location,action.voice_cmd_unprocessed),last_action.points)
            else:
                last_action = action
 
    def checkCommand(self,action):
        #self.log.info(u"{}".format(action.points))

        for cmd in SemanticConfig["commands"]:
            for search in SemanticConfig["commands"][cmd]["search"]:
                if search[0:1] == "/" and search[-1:] == "/":
                    #self.log.info(u"{} {}".format(search[1:-1],action.voice_cmd_unprocessed))
                    match = re.match(search[1:-1],action.voice_cmd_unprocessed)
                    if match:
                        number = match.group(1)
                        if number in SemanticConfig["main"]["number_mapping"]:
                            number = SemanticConfig["main"]["number_mapping"][number]
                        if number.isnumeric():
                            return cmd, SemanticConfig["commands"][cmd]["types"], number
                        return None, None, None
                else:
                    parts = action.voice_cmd_unprocessed.split(" ")
                    if search in parts:
                        return cmd, SemanticConfig["commands"][cmd]["types"], None
        return None, None, None
    
    def detectCommand(self,actions):
        for action in actions:
            # search for cmd based on voice_cmd
            cmd, item_types, argument = self.checkCommand(action)
            if cmd is not None:
                action.cmd = ItemCommand(cmd,item_types,argument)


    def fillCommandFallbacks(self,actions):
        # Fill missing commands backward
        last_cmd = None
        for action in reversed(actions):
            if action.cmd is None:
                action.cmd = last_cmd
            else:
                last_cmd = action.cmd

        # Fill missing commands forward
        last_cmd = None
        for action in actions:
            #self.log.info(u"cmd {} {}".format(cmd,item_types))
            # if no cmd found use the last one
            if action.cmd is None:
                action.cmd = last_cmd
            else:
                last_cmd = action.cmd

    def validateActions(self,actions):
        processed_items = {}
        for action in actions:
            for point in action.points:
                item_name = point.item.getName()
                #self.log.info(u"{}".format(item_name))
                if item_name in processed_items or action.cmd is None or ( point.item.getType() not in action.cmd.types and action.cmd.types[0] !=  "*" ):
                    continue
                processed_items[item_name] = True
                action.item_actions.append(ItemAction(point.item,action.cmd.cmd,action.cmd.argument))
        #self.log.info(u"{}".format(processed_items.keys()))
    
    def process(self,voice_command, fallback_location_name):
        actions = []
        voice_command = voice_command.lower()

        # check for full text phrases
        for search in self.full_phrase_terms:
            if search == voice_command:
                action = VoiceAction(search)
                for semantic_item in self.full_phrase_map[search]:
                    action.item_actions.append(ItemAction(semantic_item.item,"ON",None))
                actions.append(action)
                #self.log.info(u"{}".format(search))
                break
   
        # check for item commands
        if len(actions)==0:
            for synonym in SemanticConfig["main"]["synonyms"]:
                voice_command = voice_command.replace(synonym,SemanticConfig["main"]["synonyms"][synonym])

            sub_voice_commands = voice_command.split(SemanticConfig["main"]["phrase_separator"])
            for sub_voice_command in sub_voice_commands:
                actions.append(VoiceAction(sub_voice_command))

            self.detectLocations(actions)
            self.fillLocationsFallbacks(actions,fallback_location_name)

            self.detectPoints(actions)

            self.detectCommand(actions)

            self.fillPointFallbacks(actions)

            self.fillCommandFallbacks(actions)

            self.validateActions(actions)
 
        return actions

    def getParentByType(self,semantic_item,type):
        for parent in semantic_item.parents:
            if parent.type == "Group":
                continue
            if parent.type == type:
                return parent
            return self.getParentByType(parent,type)

    def getAnswer(self,item):
        semantic_item = self.semantic_items.semantic_items[item.getName()]
        semantic_parent = self.getParentByType(semantic_item,"Location")

        msg = None
        value = getItemState(item).toString()
        for tag in item.getTags():
            if tag not in SemanticConfig["answers"]:
                continue
            msg = SemanticConfig["answers"][tag].format(semantic_parent.item.getLabel(),value)
            break
        if msg == None:
            if value in SemanticConfig["states"]:
                value = SemanticConfig["states"][value]
            msg = SemanticConfig["answers"]["Default"].format(semantic_parent.item.getLabel(),value)
        return msg

    def applyActions(self,actions,voice_command,dry_run):
        msg = None
        missing_locations = []
        missing_points = []
        missing_cmds = []
        unsupported_cmds = []
        for action in actions:
            if len(action.item_actions) > 0:
                read_actions = filter(lambda item_action: item_action.cmd_name == "READ", action.item_actions)
                if len(read_actions) > 1:
                    msg = SemanticConfig["i18n"]["only_one_read_supported"]
                    break
                else:
                    continue
 
            if len(action.locations) == 0:
                missing_locations.append(action.voice_cmd_complete)
            elif len(action.points) == 0:
                missing_points.append(action.voice_cmd_complete)
            elif action.cmd is None:
                missing_cmds.append(action.voice_cmd_complete)
            else:
                unsupported_cmds.append(action.voice_cmd_complete)

        is_valid = False
        if msg == None:
            join_seperator = SemanticConfig["i18n"]["message_join_separator"]
            if len(actions) == len(missing_locations):
                msg = SemanticConfig["i18n"]["nothing_found"].format(voice_command)
            elif len(missing_locations) > 0:
                msg = SemanticConfig["i18n"]["nothing_found"].format(join_seperator.join(missing_locations))
            elif len(missing_points) > 0:
                msg = SemanticConfig["i18n"]["no_equipment_found_in_phrase"].format(join_seperator.join(missing_points))
            elif len(missing_cmds) > 0:
                msg = SemanticConfig["i18n"]["no_cmd_found_in_phrase"].format(join_seperator.join(missing_cmds))
            elif len(unsupported_cmds) > 0:
                msg = SemanticConfig["i18n"]["no_supported_cmd_in_phrase"].format(join_seperator.join(unsupported_cmds))
            else:
                msg = SemanticConfig["i18n"]["ok_message"]
                is_valid = True

        if is_valid:
            for action in actions:
                for item_action in action.item_actions:
                    if item_action.cmd_name == "READ":
                        msg = self.getAnswer(item_action.item)
                        #answer_data.append([item_action.item,value])
                    elif not dry_run:
                        if item_action.cmd_name == "PERCENT":
                            sendCommandIfChanged(item_action.item,item_action.cmd_argument)
                        else:
                            #self.log.info(u"postUpdate {} {}".format(item_action.item.getName(),item_action.cmd_name))
                            sendCommandIfChanged(item_action.item,item_action.cmd_name)
  
        return msg, is_valid
 
    def parseData(self,input):
        data = input.split("|")
        if len(data) == 1:
            return [ data[0], None ]
        else:
            client_id = data[1].replace("amzn1.ask.device.","")
            fallback_location = AlexaDevices[client_id] if client_id in AlexaDevices else None
            return [ data[0], fallback_location ]

    def execute(self, module, input):
        postUpdate("VoiceMessage","")

        voice_command, fallback_location_name = self.parseData(input['event'].getItemState().toString())

        self.log.info(u"Process: '{}', Location: '{}'".format(voice_command, fallback_location_name))

        actions = self.process(voice_command, fallback_location_name)

        msg, is_valid = self.applyActions(actions,voice_command,False)

        postUpdate("VoiceMessage",msg)
        
@rule("voice_command.py")
class TestRule:
    def __init__(self):
        voice_command_rule = VoiceCommandRule()
        for case in Cases['enabled']:
            if "client_id" in case:
                voice_command, fallback_location_name = voice_command_rule.parseData(u"{}|{}".format(case['phrase'],case['client_id']))
            else:
                voice_command, fallback_location_name = voice_command_rule.parseData(case['phrase'])
            actions = voice_command_rule.process(voice_command, fallback_location_name)

            msg, is_valid = voice_command_rule.applyActions(actions,voice_command,True)

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
                        if item_action.item.getName() == case_item and item_action.cmd_name == case_cmd:
                            item_actions_applied.append(item_action)
                            item_actions_skipped.remove(item_action)
                            case_actions_excpected.remove(case_action)
   
            if (("is_valid" in case and case["is_valid"] == is_valid) or is_valid ) \
                and len(item_actions_skipped) == 0 and len(item_actions_applied) == len(case["items"]):
                self.log.info(u"OK  - Input: '{}' - MSG: '{}'".format(voice_command,msg))
            else:
                self.log.info(u"ERR - Input: '{}' - MSG: '{}'".format(voice_command,msg))
                for case_action in case_actions_excpected:
                    self.log.info(u"       MISSING     => {} => {}".format(case_action[0],case_action[1]))
                for item_action in item_actions_skipped:
                    self.log.info(u"       UNEXCPECTED => {} => {}".format(item_action.item.getName(),item_action.cmd_name))
                for item_action in item_actions_applied:
                    self.log.info(u"       MATCH       => {} => {}".format(item_action.item.getName(),item_action.cmd_name))

                items = []
                for item_action in item_actions_skipped:
                    items.append(u"[\"{}\",\"{}\"]".format(item_action.item.getName(),item_action.cmd_name))
                for item_action in item_actions_applied:
                    items.append(u"[\"{}\",\"{}\"]".format(item_action.item.getName(),item_action.cmd_name))

                self.log.info(u"\n\n[{}]\n\n".format(",".join(items)))
                raise Exception("Wrong detection")

    def execute(self, module, input):
        pass