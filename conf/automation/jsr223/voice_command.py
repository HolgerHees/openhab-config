from shared.helper import rule, postUpdate

from core.triggers import ItemStateUpdateTrigger

from alexa.configuration import allAlexaDevices

#https://github.com/openhab/openhab-core/blob/master/bundles/org.openhab.core.semantics/model/SemanticTags.csv
from alexa.semantic_type import SemanticTagsAsCsv
from alexa.semantic_test import Cases

from core.actions import HTTP

import re

import json
 
config = {
    "i18n": {
        "nothing_found": u"Ich habe '{}' nicht verstanden",
        "no_equipment_found_in_phrase": u"Ich habe das Gerät in '{}' nicht erkannt",
        "no_cmd_found_in_phrase": u"Ich habe die Aktion in '{}' nicht erkannt",
        "no_supported_cmd_in_phrase": u"Die Aktion wird für das Gerät in '{}' nicht unterstützt",
        "message_join_separator": u" und ",
        "ok_message": "ok"
    },
    "main": {
        "phrase_separator": " und ",
        "phrase_matcher": u"(.*[^a-zA-Z]+|^){}(.*|$)",
        "phrase_sub": ["vorne","hinten","links","rechts","oben","unten"],
        "phrase_equipment": "eOther_Scenes",
        "synonyms": {
            "warm": "temperatur",
            "kalt": "temperatur",
            "feucht": "feuchtigkeit",
            "trocken": "feuchtigkeit",
            "luftfeuchtigkeit": "feuchtigkeit",
        },
        "number_mapping": {
            u"zehn": "10",
            u"zwanzig": "20",
            u"dreizig": "30",
            u"vierzig": "40",
            u"fünfzig": "50",
            u"sechzig": "60",
            u"siebzig": "70",
            u"achtzig": "80",
            u"neunzig": "90",
            u"hundert": "100",
        }
    }, 
    "commands": {
        "OFF": { "search": ["aus","ausschalten","beenden","beende","deaktiviere","stoppe","stoppen"], "types": ["Switch","Dimmer"] },
        "ON": { "search": ["an","ein","einschalten","starten","aktiviere","aktivieren"], "types": ["Switch","Dimmer"] },
        "DOWN": { "search": ["runter","schliessen"], "types": ["Rollershutter"] },
        "UP": { "search": ["hoch","rauf","öffnen"], "types": ["Rollershutter"] },
        "PERCENT": { "search": [u"/.* ([0-9a-zA-ZäÄöÖüÜß]+)[\\s]*(prozent|%).*/"], "types": ["Dimmer"] },
        "READ": { "search": ["wie","wieviel","was","ist","sind"], "types": ["Number","String","Contact"] }
    }
}

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
    def __init__(self,cmd_name,item_name,cmd_argument):
        self.cmd_name = cmd_name
        self.item_name = item_name
        self.cmd_argument = cmd_argument

class SemanticItem:
    def __init__(self,item,type):
        self.item = item
        self.type = type
        self.label = []
        self.tags = []
        self.synonyms = []
        self.search_terms = []

        self.children = []

    def __repr__(self):
        return self.item.getName() + " (" + str(self.label) + "|" + str(self.tags) + "|" + str(self.synonyms) + ")"

class SemanticData:
    def __init__(self):
        lines = SemanticTagsAsCsv.split("\n")
        semantic_tags = {}
        for line in lines:
            columns = line.split(",")
            type = columns[0]
            tag = columns[1]

            if type not in semantic_tags:
                semantic_tags[type] = []
            semantic_tags[type].append(tag)

        # build semantic items
        self.semantic_items = {}
        for item in ir.getItems():
            type = self.getType(semantic_tags,item)
            semanticItem = SemanticItem(item,type)
            self.semantic_items[semanticItem.item.getName()] = semanticItem

        # append label, synonyms and tags
        response = HTTP.sendHttpGetRequest("http://openhab:8080/rest/habot/attributes")
        json_data = json.loads(response.encode('utf-8'))
        for item_name in json_data:
            semantic_item = self.semantic_items[item_name]
            for attribute in json_data[item_name]:
                if attribute['inherited']:
                    continue
                if attribute['source'] == "LABEL":
                    semantic_item.label.append(attribute['value'].lower())
                elif attribute['source'] == "TAG":
                    semantic_item.tags.append(attribute['value'].lower())
                elif attribute['source'] == "METADATA":
                    semantic_item.synonyms.append(attribute['value'].lower())
            semantic_item.search_terms = list(set(semantic_item.label + semantic_item.synonyms + semantic_item.tags))

        # prepare semantic locations and children
        location_map = {}
        self.root_locations = []
        for semantic_item in self.semantic_items.values():
            if semantic_item.item.getType() == "Group":
                children = semantic_item.item.getMembers()
                for item in children:
                    semantic_item.children.append(self.semantic_items[item.getName()])

                if semantic_item.type == "Location":
                    location_map[semantic_item.item.getName()] = semantic_item
                    if len(semantic_item.item.getGroupNames()) == 0:
                        self.root_locations.append(semantic_item)

        # prepare regex matcher
        self.semantic_search_regex = {}
        for semantic_item in self.semantic_items.values():
            for search_term in semantic_item.search_terms:
                if search_term in self.semantic_search_regex:
                    continue
                self.semantic_search_regex[search_term] = re.compile(config["main"]["phrase_matcher"].format(search_term))
 
    def getType(self,semantic_tags,item):
        item_tags = item.getTags()
        for tag in semantic_tags["Location"]:
            if tag not in item_tags:
                continue
            return "Location"
        for tag in semantic_tags["Equipment"]:
            if tag not in item_tags:
                continue
            return "Equipment"
        for tag in semantic_tags["Point"]:
            if tag not in item_tags:
                continue
            return "Point"
        return None

semantic_data = SemanticData()

@rule("voice_command.py")
class VoiceCommandRule:
    def __init__(self):
        self.triggers = [ ItemStateUpdateTrigger("VoiceCommand") ]
        self.full_phrase_map, self.full_phrase_terms = self.buildSearchMap(semantic_data.semantic_items[config["main"]["phrase_equipment"]].children)
 
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
                semantic_item = semantic_data.semantic_items[item.getName()]
                #self.log.info(u" => {}".format(item.getName()))
                if semantic_item.type == type:
                    result.append(semantic_item)
                else:
                    result = result + self.getItemsByType(semantic_item,type)
        return result

    def _searchItems(self,items,unprocessed_search,items_to_skip,recursive,is_sub_search,security_counter = 0):
        security_counter = security_counter + 1
        if security_counter >= 10:
            raise Exception("_searchItems: security counter matched. more then 10 loops.")
        #self.log.info(u"_searchItems: {}".format(','.join([str(item.item.getName()) for item in items]) ))
        # check for matches in items
        matched_items = []
        matched_search = None
        search_map, search_terms = self.buildSearchMap(items)
        for search_term in search_terms:
            if not is_sub_search and search_term in config["main"]["phrase_sub"]:
                continue
  
            if semantic_data.semantic_search_regex[search_term].match(unprocessed_search):
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
                    semantic_member = semantic_data.semantic_items[member.getName()]
                    if member.getType() != "Group" or semantic_member.type != item.type:
                        continue
                    to_check.append(semantic_member)
        
            # check children for matches
            if len(to_check)>0:
                #self.log.info(u"to_check: {}".format(','.join([str(item.item.getName()) for item in to_check])))
                _matched_items, _matched_search, _unprocessed_search = self._searchItems(to_check,matched_search if matched_search is not None else unprocessed_search,items_to_skip,recursive,is_sub_search,security_counter)
                if matched_search == None:
                    unprocessed_search = _unprocessed_search
                    matched_search = _matched_search
                matched_items += _matched_items 
    
        if matched_search != None:
            unprocessed_search = unprocessed_search.replace(search_term,"")

        return matched_items, matched_search, unprocessed_search

    def searchItems(self,items,unprocessed_search,items_to_skip,recursive):
        matched_items = []
        security_counter = 0
        while True:
            security_counter = security_counter + 1
            if security_counter >= 10:
                raise Exception(u"searchItems: security counter matched. more then 10 loops.")
            #self.log.info(u"search items")
            _items, _matched_search, _unprocessed_search = self._searchItems(items,unprocessed_search,items_to_skip,recursive,len(matched_items)>0)
            if len(_items) == 0:
                break
            matched_items = _items
            items = matched_items
            unprocessed_search = _unprocessed_search

        #self.log.info(u"found items: {}".format(','.join([str(item.item.getName()) for item in matched_items]) ))
        #raise Exception("test")
        return matched_items, unprocessed_search

    def detectLocations(self,actions,client_id):
        for action in actions:
            # search for locations
            matched_locations, unprocessed_search = self.searchItems(semantic_data.root_locations,action.voice_cmd_unprocessed,[],True)
            action.voice_cmd_unprocessed = unprocessed_search
            action.voice_cmd_without_location = unprocessed_search
            action.locations = matched_locations

    def fillLocationsFallbacks(self,actions,client_id):
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
        if client_id != None:
            for action in actions:
                if len(action.locations) != 0:
                    continue
                location_name = allAlexaDevices[client_id]
                action.locations = [ semantic_data.semantic_items[location_name] ]

    def checkPoints(self,action,unprocessed_search,items_to_skip):
        #self.log.info(u"checkPoints")
        equipments = []
        for location in action.locations:
            # search for equipments    
            #self.log.info(u"  location: '{}', unprocessed_search: '{}'".format(location,unprocessed_search))
            equipments += self.getItemsByType(location,"Equipment")

        matched_equipments, unprocessed_search = self.searchItems(equipments,unprocessed_search,items_to_skip,True)
 
        # check points of equipments 
        if len(matched_equipments) > 0:
            points = []
            #point_matches = False
            #processed_search_terms = []
            for equipment in matched_equipments:
                #self.log.info(u"  equipment: '{}', unprocessed_search: '{}'".format(equipment.item.getName(),unprocessed_search))
                points += self.getItemsByType(equipment,"Point")

            matched_points, unprocessed_search = self.searchItems(points,unprocessed_search,items_to_skip,False)

            # add matched points or all equipment points if there are no matches
            action.points = points if len(matched_points) == 0 else matched_points
            return unprocessed_search

        # check points of locations
        points = []
        for location in action.locations:
            points += self.getItemsByType(location,"Point")

        matched_points, unprocessed_search = self.searchItems(points,unprocessed_search,items_to_skip,False)
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

        for cmd in config["commands"]:
            for search in config["commands"][cmd]["search"]:
                if search[0:1] == "/" and search[-1:] == "/":
                    #self.log.info(u"{} {}".format(search[1:-1],action.voice_cmd_unprocessed))
                    match = re.match(search[1:-1],action.voice_cmd_unprocessed)
                    if match:
                        number = match.group(1)
                        if number in config["main"]["number_mapping"]:
                            number = config["main"]["number_mapping"][number]
                        if number.isnumeric():
                            return cmd, config["commands"][cmd]["types"], number
                        return None, None, None
                else:
                    parts = action.voice_cmd_unprocessed.split(" ")
                    #self.log.info(u"found {}".format(parts))
                    #self.log.info(u"found {}".format(search))
                    if search in parts:
                        return cmd, config["commands"][cmd]["types"], None
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
                if item_name in processed_items or action.cmd is None or point.item.getType() not in action.cmd.types:
                    continue
                processed_items[item_name] = True
                action.item_actions.append(ItemAction(action.cmd.cmd,item_name,action.cmd.argument))
        #self.log.info(u"{}".format(processed_items.keys()))

    def getResultMessage(self,actions,voice_command):
        msg = []
        missing_locations = []
        missing_points = []
        missing_cmds = []
        unsupported_cmds = []
        for action in actions:
            if len(action.item_actions) > 0:
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
        join_seperator = config["i18n"]["message_join_separator"]
        if len(actions) == len(missing_locations):
            msg = config["i18n"]["nothing_found"].format(voice_command)
        elif len(missing_locations) > 0:
            msg = config["i18n"]["nothing_found"].format(join_seperator.join(missing_locations))
        elif len(missing_points) > 0:
            msg = config["i18n"]["no_equipment_found_in_phrase"].format(join_seperator.join(missing_points))
        elif len(missing_cmds) > 0:
            msg = config["i18n"]["no_cmd_found_in_phrase"].format(join_seperator.join(missing_cmds))
        elif len(unsupported_cmds) > 0:
            msg = config["i18n"]["no_supported_cmd_in_phrase"].format(join_seperator.join(unsupported_cmds))
        else:
            msg = config["i18n"]["ok_message"]
            is_valid = True

        return msg, is_valid
    
    def process(self,voice_command, client_id):
        actions = []
        voice_command = voice_command.lower()

        # check for full text phrases
        for search in self.full_phrase_terms:
            if search == voice_command:
                action = VoiceAction(search)
                for semantic_item in self.full_phrase_map[search]:
                    action.item_actions.append(ItemAction("ON",semantic_item.item.getName(),None))
                actions.append(action)
                #self.log.info(u"{}".format(search))
                break
   
        # check for item commands
        if len(actions)==0:
            for synonym in config["main"]["synonyms"]:
                voice_command = voice_command.replace(synonym,config["main"]["synonyms"][synonym])

            sub_voice_commands = voice_command.split(config["main"]["phrase_separator"])
            for sub_voice_command in sub_voice_commands:
                actions.append(VoiceAction(sub_voice_command))

            self.detectLocations(actions,client_id)
            self.fillLocationsFallbacks(actions,client_id)

            self.detectPoints(actions)

            self.detectCommand(actions)

            self.fillPointFallbacks(actions)

            self.fillCommandFallbacks(actions)

            self.validateActions(actions)
 
        #item_actions = []
        #for action in actions:
        #    if len(action.item_actions) == 0:
        #        item_actions.append(ItemAction(action.voice_cmd_complete,None,None,None))
        #    else:
        #        for item_action in action.item_actions:
        #            item_actions.append(item_action)

        return actions
 
        #for attribute in semantic_data.item_attributes:
        #    self.log.info(u"{}".format(semantic_data.item_attributes[attribute]))

    def parseData(self,input):
        data = input.split("|")
        if len(data) == 1:
            return [ data[0], None ]
        else:
            client_id = data[1].replace("amzn1.ask.device.","")
            return [ data[0], client_id ]

    def execute(self, module, input):
        voice_command, client_id = self.parseData(input['event'].getItemState().toString())
        actions = self.process(voice_command, client_id)
        msg, is_valid = voice_command_rule.getResultMessage(actions,voice_command)
        if is_valid:
            for action in actions:
                for item_action in action.item_actions:
                    if item_action.cmd_name == "READ":
                        value = getItemState(item_action.item_name)
                        # TODO - FORMAT
                        msg = value.toString()
                    elif item_action.cmd_name == "PERCENT":
                        postUpdate(item_action.item_name,item_action.cmd_argument)
                    else:
                        postUpdate(item_action.item_name,item_action.cmd_name)
 
        postUpdate("VoiceMessage",msg)
        
@rule("voice_command.py")
class TestRule:
    def __init__(self):
        voice_command_rule = VoiceCommandRule()
        for case in Cases['enabled']:
            if "client_id" in case:
                voice_command, client_id = voice_command_rule.parseData(u"{}|{}".format(case['phrase'],case['client_id']))
            else:
                voice_command, client_id = voice_command_rule.parseData(case['phrase'])
            actions = voice_command_rule.process(voice_command, client_id)

            msg, is_valid = voice_command_rule.getResultMessage(actions,voice_command)

            item_actions_skipped = []
            for action in actions:
                for item_action in action.item_actions:
                    item_actions_skipped.append(item_action)
                    #self.log.info(u"{}".format(item_action.item_name))

            case_actions_excpected = []
            item_actions_applied = []
            for case_action in case["items"]:
                case_actions_excpected.append(case_action)
                case_item = case_action[0]
                case_cmd = case_action[1]
                for action in actions:
                    for item_action in action.item_actions:
                        if item_action.item_name == case_item and item_action.cmd_name == case_cmd:
                            item_actions_applied.append(item_action)
                            item_actions_skipped.remove(item_action)
                            case_actions_excpected.remove(case_action)

            if len(item_actions_skipped) == 0 and len(item_actions_applied) == len(case["items"]):
                self.log.info(u"OK  - Input: '{}' - MSG: '{}'".format(voice_command,msg))
            else:
                self.log.info(u"ERR - Input: '{}' - MSG: '{}'".format(voice_command,msg))
                for case_action in case_actions_excpected:
                    self.log.info(u"       MISSING     => {} => {}".format(case_action[0],case_action[1]))
                for item_action in item_actions_skipped:
                    self.log.info(u"       UNEXCPECTED => {} => {}".format(item_action.item_name,item_action.cmd_name))
                for item_action in item_actions_applied:
                    self.log.info(u"       MATCH       => {} => {}".format(item_action.item_name,item_action.cmd_name))

                items = []
                for item_action in item_actions_skipped:
                    items.append(u"[\"{}\",\"{}\"]".format(item_action.item_name,item_action.cmd_name))
                for item_action in item_actions_applied:
                    items.append(u"[\"{}\",\"{}\"]".format(item_action.item_name,item_action.cmd_name))

                self.log.info(u"\n\n[{}]\n\n".format(",".join(items)))
                raise Exception("Wrong detection")

    def execute(self, module, input):
        pass                       