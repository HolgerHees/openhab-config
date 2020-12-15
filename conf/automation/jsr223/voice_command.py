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
        "nothing_found": "ich habe leider keine Geräte gefunden",
        "nothing_found_in_phrase": "den Teil '{phrase}' habe ich nicht verstanden",
        "no_area_found_in_phrase": "den Ort hab ich in '{phrase}' nicht erkannt",
        "no_cmd_found_in_phrase": "die Aktion habe ich in '{phrase}' nicht erkannt",
        "too_much_found_in_phrase": "für den Teil '{phrase}' habe ich mehr als ein Gerät gefunden",
        "no_devices_found_in_phrase": "für den Teil '{phrase}' habe ich kein Gerät gefunden",
        "ask_to_repeat_everything": "versuche es einfach nochmal",
        "ask_to_repeat_part": "versuche den Teil nochmal",
        "message_join_separator": " und ",
        "message_error_separator": " aber ",
        "ok_message": "ok",
        "help_message": "sage marvin zum beispiel schalte das licht im wohnzimmer an",
        "help_ask_message": "versuche es einfach"
    },
    "main": {
        "phrase_separator": " und ",
        "phrase_matcher": u"(.*[^a-zA-Z]+|^){}(.*|$)",
        "phrase_sub": ["vorne","hinten","links","rechts","oben","unten"],
        "phrase_equipment": "eOther_Scenes"
    },
    "commands": {
        "OFF": { "search": ["aus","ausschalten","beenden","beende","deaktiviere","stoppe","stoppen"], "types": ["Switch","Dimmer"] },
        "ON": { "search": ["an","ein","einschalten","starten","aktiviere","aktivieren"], "types": ["Switch","Dimmer"] },
        "DOWN": { "search": ["runter","schliessen"], "types": ["Rollershutter"] },
        "UP": { "search": ["hoch","rauf","öffnen"], "types": ["Rollershutter"] },
        "PERCENT": { "search": [u"/.* ([0-9a-zA-ZäÄöÖüÜß]+)[\\s]*(prozent|%).*/"], "types": ["Dimmer"] },
        "READ": { "search": ["wie","wieviel","was"], "types": ["Number","String"] }
    }
}

class VoiceAction:
    def __init__(self,voice_cmd):
        self.voice_cmd_complete = voice_cmd
        self.voice_cmd_unprocessed = voice_cmd
        self.locations = []
        self.points = []

        self.item_cmd = None
        self.item_actions = []

class ItemCommand:
    def __init__(self,cmd,types):
        self.cmd = cmd
        self.types = types

class ItemAction:
    def __init__(self,cmd,item):
        self.cmd = cmd
        self.item = item

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
 
        # prepare location search map
        self.location_search_map = {}
        for semantic_item in location_map.values():
            #parent_names = semantic_item.item.getGroupNames()
            #for parent_name in parent_names:
            #    semantic_item.parents.append(self.semantic_items[parent_name])

            for search_term in semantic_item.search_terms:
                if search_term not in self.location_search_map:
                    self.location_search_map[search_term] = []
                self.location_search_map[search_term].append(semantic_item)
 
        self.location_search_terms = sorted(self.location_search_map, key=len, reverse=True)
 
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

    def _searchItems(self,items,unprocessed_search,recursive,is_sub_search):
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
                matched_search = search_term
                #self.log.info(u"matched_items: {} {}".format(search_term,','.join([str(item.item.getName()) for item in matched_items])))
                break
 
        if recursive:
            # collect items which does not match and collect their children of same type
            missing_items = list(set(items) - set(matched_items))
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
                _matched_items, _matched_search, _unprocessed_search = self._searchItems(to_check,matched_search if matched_search is not None else unprocessed_search,recursive,is_sub_search)
                if matched_search == None:
                    unprocessed_search = _unprocessed_search
                    matched_search = _matched_search
                matched_items += _matched_items 
    
        if matched_search != None:
            unprocessed_search = unprocessed_search.replace(search_term,"")

        return matched_items, matched_search, unprocessed_search

    def searchItems(self,items,unprocessed_search,recursive):
        matched_items = []
        while True:
            #self.log.info(u"search items")
            _items, _matched_search, _unprocessed_search = self._searchItems(items,unprocessed_search,recursive,len(matched_items)>0)
            if len(_items) == 0:
                break
            matched_items = _items
            items = matched_items
            unprocessed_search = _unprocessed_search

        #self.log.info(u"found items: {}".format(','.join([str(item.item.getName()) for item in matched_items]) ))
        #raise Exception("test")
        return matched_items, unprocessed_search

    def detectLocations(self,actions,client_id):
        last_locations = []
        for action in actions:
            # search for locations
            matched_locations, unprocessed_search = self.searchItems(semantic_data.root_locations,action.voice_cmd_unprocessed,True)
            action.voice_cmd_unprocessed = unprocessed_search
            action.locations = matched_locations

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
                action.locations = [ semantic_data.locations[location_name] ]
 
    def checkPoints(self,action,unprocessed_search):
        equipments = []
        for location in action.locations:
            # search for equipments    
            #self.log.info(u"  location: {} {}".format(location,unprocessed_search))
            equipments += self.getItemsByType(location,"Equipment")

        matched_equipments, unprocessed_search = self.searchItems(equipments,unprocessed_search,True)
    
        # check points of equipments 
        if len(matched_equipments) > 0:
            points = []
            #point_matches = False
            #processed_search_terms = []
            for equipment in matched_equipments:
                #self.log.info(u"  equipment, leftover: '{}', item: {}".format(cmd,equipment.item.getName()))
                points += self.getItemsByType(equipment,"Point")

            matched_points, unprocessed_search = self.searchItems(points,unprocessed_search,False)

            # add matched points or all equipment points if there are no matches
            action.points = points if len(matched_points) == 0 else matched_points
            return unprocessed_search

        # check points of locations
        points = []
        for location in action.locations:
            points += self.getItemsByType(location,"Point")

        matched_points, unprocessed_search = self.searchItems(points,unprocessed_search,False)
        action.points = matched_points

        return unprocessed_search 

    def detectPoints(self,actions):
        last_cmd = None
        for action in actions:
            # search for points based on voice_cmd
            voice_cmd_unprocessed = self.checkPoints(action,action.voice_cmd_unprocessed)
            if voice_cmd_unprocessed != None:
                #self.log.info(voice_cmd_unprocessed)
                action.voice_cmd_unprocessed = voice_cmd_unprocessed

            # if no points where found search again based on the last cmd with points
            if len(action.points) == 0:
                if last_cmd != None:
                    self.checkPoints(action,last_cmd)
            else:
                last_cmd = action.voice_cmd_complete
        
        #self.log.info(u"done")

        # Fill missing points backward
        last_cmd = None
        for action in reversed(actions):
            if len(action.points) == 0:
                if last_cmd != None:
                    self.checkPoints(action,last_cmd)
            else:
                last_cmd = action.voice_cmd_complete

    def checkCommand(self,action):
        for cmd in config["commands"]:
            for search in config["commands"][cmd]["search"]:
                if search[0:1] == "/" and search[-1:] == "/":
                    #self.log.info(u"{} {}".format(search[1:-1],action.voice_cmd_unprocessed))
                    if re.match(search[1:-1],action.voice_cmd_unprocessed):
                        return cmd, config["commands"][cmd]["types"]
                else:
                    parts = action.voice_cmd_unprocessed.split(" ")
                    #self.log.info(u"found {}".format(parts))
                    #self.log.info(u"found {}".format(search))
                    if search in parts:
                        return cmd, config["commands"][cmd]["types"]
        return None, None

    def detectCommand(self,actions):
        last_cmd = None
        for action in actions:
            # search for cmd based on voice_cmd
            cmd, item_types = self.checkCommand(action)
            #self.log.info(u"cmd {} {}".format(cmd,item_types))
            # if no cmd found use the last one
            if cmd is None:
                action.cmd = last_cmd
            else:
                action.cmd = ItemCommand(cmd,item_types)
                last_cmd = action.cmd

        # Fill missing locations backward
        last_cmd = None
        for action in reversed(actions):
            if action.cmd is None:
                action.cmd = last_cmd
            else:
                last_cmd = action.cmd

    def validateActions(self,actions):
        for action in actions:
            for point in action.points:
                if action.cmd is None or point.item.getType() not in action.cmd.types:
                    continue
                action.item_actions.append(ItemAction(action.cmd.cmd,point.item))

    def process(self,voice_command, client_id, fallback_room):
        sub_voice_commands = voice_command.lower().split(config["main"]["phrase_separator"])
        actions = []
        for sub_voice_command in sub_voice_commands:
            actions.append(VoiceAction(sub_voice_command))

        self.detectLocations(actions,client_id)

        self.detectPoints(actions)

        self.detectCommand(actions)

        self.validateActions(actions)

        item_actions = {}
        for action in actions:
            for item_action in action.item_actions:
                #self.log.info(u"{}".format(item_action.item.getName()))
                item_actions[item_action.item.getName()] = item_action

        return list(item_actions.values())
 
        #for attribute in semantic_data.item_attributes:
        #    self.log.info(u"{}".format(semantic_data.item_attributes[attribute]))

    def parseData(self,input):
        data = input.split("|")
        if len(data) == 1:
            return [ data[0], None, None ]
        else:
            return [ data[0], data[1], allAlexaDevices[data[1]] ]

    def execute(self, module, input):
        voice_command, client_id, fallback_room = self.parseData(input['event'].getItemState().toString())
        self.process(voice_command, client_id, fallback_room)
        
@rule("voice_command.py")
class TestRule:
    def __init__(self):
        voice_command_rule = VoiceCommandRule()
        for case in Cases['enabled']:
            voice_command, client_id, fallback_room = voice_command_rule.parseData(case['phrase'])
            item_actions = voice_command_rule.process(voice_command, client_id, fallback_room)
 
            case_actions_excpected = []
            item_actions_processed = []
            for case_action in case["items"]:
                case_actions_excpected.append(case_action)
                case_item = case_action[0]
                case_cmd = case_action[1]
                for item_action in item_actions:
                    if item_action.item.getName() == case_item and item_action.cmd == case_cmd:
                        item_actions.remove(item_action)
                        item_actions_processed.append(item_action)
                        case_actions_excpected.remove(case_action)
                        break

            if len(item_actions) == 0 and len(item_actions_processed) > 0:
                self.log.info(u"OK  - Input: '{}'".format(voice_command))
            else:
                self.log.info(u"ERR - Input: '{}'".format(voice_command))
                for case_action in case_actions_excpected:
                    self.log.info(u"       MISSING     => {} => {}".format(case_action[0],case_action[1]))
                for item_action in item_actions:
                    self.log.info(u"       UNEXCPECTED => {} => {}".format(item_action.item.getName(),item_action.cmd))
                for item_action in item_actions_processed:
                    self.log.info(u"       MATCH       => {} => {}".format(item_action.item.getName(),item_action.cmd))
                raise Exception("Wrong detection")

    def execute(self, module, input):
        pass 