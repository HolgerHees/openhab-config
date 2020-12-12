from shared.helper import rule, postUpdate

from core.triggers import ItemStateUpdateTrigger

from alexa import allAlexaDevices

#https://github.com/openhab/openhab-core/blob/master/bundles/org.openhab.core.semantics/model/SemanticTags.csv
from semantic import SemanticTagsAsCsv
from semantic_test import Cases

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
        "phrase_matcher": u"(.*[^a-zA-Z]+|^){}(.*|$)"
    },
    "commands": {
        "OFF": { "search": ["aus","ausschalten","beenden","beende","deaktiviere","stoppe","stoppen"], "types": ["Switch","Dimmer"] },
        "ON": { "search": ["an","ein","einschalten","starten","aktiviere","aktivieren"], "types": ["Switch","Dimmer"] },
        "DOWN": { "search": ["runter","schliessen"], "types": ["Rollershutter"] },
        "UP": { "search": ["hoch","öffnen"], "types": ["Rollershutter"] },
        "PERCENT": { "search": [u"/.* ([0-9a-zA-ZäÄöÖüÜß]+)[\\s]*(prozent|%).*/"], "types": ["Dimmer"] },
        "READ": { "search": ["wie","wieviel","was"], "types": ["Number","String"] }
    }
}

class VoiceAction:
    def __init__(self,voice_cmd):
        self.voice_cmd_complete = voice_cmd
        self.voice_cmd_unprocessed = voice_cmd
        self.locations = {}
        self.equipments = {}
        self.points = {}

        self.item_cmd = None
        self.item_actions = {}

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
            semantic_item.search_terms = semantic_item.label + semantic_item.synonyms + semantic_item.tags

        # prepare semantic locations
        self.location_search_map = {}
        for semantic_item in self.semantic_items.values():
            if semantic_item.type == "Location":
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

    def parseData(self,input):
        data = input.split("|")
        if len(data) == 1:
            return [ data[0], None, None ]
        else:
            return [ data[0], data[1], allAlexaDevices[data[1]] ]

    def getByType(self,parent,type):
        result = []
        if parent.getType() == "Group":
            #self.log.info(u" => {} {}".format(parent.getName(),parent.getType()))
            items = parent.getMembers()
            for item in items:
                #self.log.info(u" => {}".format(item.getName()))
                if semantic_data.semantic_items[item.getName()].type == type:
                    result.append(semantic_data.semantic_items[item.getName()])
                result = result + self.getByType(item,type)
        return result

    def buildSearchMap(self,items):
        search_map = {}
        for semantic_item in items:
            for search_term in semantic_item.search_terms:
                if search_term not in search_map:
                    search_map[search_term] = []
                search_map[search_term].append(semantic_item)
        search_terms = sorted(search_map, key=len, reverse=True)
        return search_map, search_terms

    def getByTypeSorted(self,parent,type):
        result = self.getByType(parent,type)
        search_map, search_terms = self.buildSearchMap(result)
        return search_map, search_terms, result

    def searchSemanticItems(self,search_map,search_terms,unprocessed_search):
        # search for items and reduce result until no new matches found
        # like first matches 'indirekt'
        # then matches 'couch' etc
        matched_items = []
        processed_search = []
        while len(search_terms) > 0:
            _matched_items = []
            for search_term in search_terms:
                if not re.match(config["main"]["phrase_matcher"].format(search_term), unprocessed_search):
                    continue
                processed_search.append(search_term)
                unprocessed_search = unprocessed_search.replace(search_term,"")
                _matched_items += search_map[search_term]
                break
            if len(_matched_items) > 0:
                matched_items = _matched_items
            search_map, search_terms = self.buildSearchMap(_matched_items)
        return matched_items, processed_search, unprocessed_search

    def detectLocations(self,actions,client_id):
        last_locations = {}
        for action in actions:
            # search for locations
            matched_locations, processed_search, unprocessed_search = self.searchSemanticItems(semantic_data.location_search_map,semantic_data.location_search_terms,action.voice_cmd_unprocessed)
            action.voice_cmd_unprocessed = unprocessed_search

            for location in matched_locations:
                action.locations[location.item.getName()] = location

            # if no location found use the last one
            if len(action.locations) == 0:
                action.locations = last_locations
            else:
                last_locations = action.locations
 
        # Fill missing locations backward
        last_locations = {}
        for action in reversed(actions):
            if len(action.locations) == 0:
                action.locations = last_locations
            else:
                last_locations = action.locations

        # Fill missing locations with fallbacks
        if client_id != None:
            for action in actions:
                if len(action.locations.keys()) != 0:
                    continue
                location_name = allAlexaDevices[client_id]
                action.locations = { location_name: semantic_data.locations[location_name] }
     
    def checkPoints(self,action,cmd):
        matched_equipments = []
        processed_search = []
        for location in action.locations.values():
            # search for equipments    
            # self.log.info(u"LOCATION: {} {}".format(location,cmd))
            equipment_search_map, equipment_search_terms,all_equipments = self.getByTypeSorted(location.item,"Equipment")
            _matched_equipments, _processed_search, unprocessed_search = self.searchSemanticItems(equipment_search_map,equipment_search_terms,cmd)
            matched_equipments = matched_equipments + _matched_equipments
            processed_search = processed_search + _processed_search

        # remove processed search words
        for search in processed_search:
            cmd = cmd.replace(search,"")
     
        # check points of equipments 
        if len(matched_equipments) > 0:
            processed_search_terms = []
            point_matches = False
            all_points = []
            for equipment in matched_equipments:
                #self.log.info(u"  equipment, leftover: '{}', item: {}".format(cmd,equipment.item.getName()))
                point_search_map, point_search_terms,equipment_points = self.getByTypeSorted(equipment.item,"Point")
                all_points = all_points + equipment_points

                # add all points which matches to cmd
                for point_search_term in point_search_terms:
                    if re.match(config["main"]["phrase_matcher"].format(point_search_term), cmd):
                        for point in point_search_map[point_search_term]:
                            #self.log.info(u"point '{}' {}".format(point_search_term,point.item))
                            action.points[point.item.getName()] = point
                        processed_search_terms.append(point_search_term)
                        point_matches = True
                        break

            # if no points where found, add all points
            if not point_matches:
                #self.log.info("test2")
                for point in all_points:
                    action.points[point.item.getName()] = point

            # clean cmd's
            for processed_search_term in processed_search_terms:
                cmd = cmd.replace(processed_search_term,"")
            #self.log.info(u"  unprocessed: {}".format(cmd))

            return cmd

        # no equipments matches, search for all points in location
        #self.log.info(u"{}".format("------"))
        point_search_map, point_search_terms, location_points = self.getByTypeSorted(location.item,"Point")
        #self.log.info(u"3 {}".format(point_search_term))
        for point_search_term in point_search_terms:
            #elf.log.info(u"{} {} {}".format(point_search_term,cmd,point_search_map[point_search_term]))
            if re.match(config["main"]["phrase_matcher"].format(point_search_term),cmd):
                for point in point_search_map[point_search_term]:
                    action.points[point.item.getName()] = point
                cmd = cmd.replace(point_search_term,"")
                return cmd
            #self.log.info(u"done")

        return None

    def detectPoints(self,actions):
        last_cmd = None
        for action in actions:
            # search for points based on voice_cmd
            voice_cmd_unprocessed = self.checkPoints(action,action.voice_cmd_unprocessed)
            if voice_cmd_unprocessed != None:
                #self.log.info(voice_cmd_unprocessed)
                action.voice_cmd_unprocessed = voice_cmd_unprocessed

            # if no points where found search again based on the last cmd with points
            if len(action.points.values()) == 0:
                if last_cmd != None:
                    self.checkPoints(action,last_cmd)
            else:
                last_cmd = action.voice_cmd_complete
        
        #self.log.info(u"done")

        # Fill missing points backward
        last_cmd = None
        for action in reversed(actions):
            if len(action.points.values()) == 0:
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
                if action.cmd is None or action.points[point].item.getType() not in action.cmd.types:
                    continue
                action.item_actions[point] = ItemAction(action.cmd.cmd,action.points[point].item)

    def process(self,voice_command, client_id, fallback_room):
        sub_voice_commands = voice_command.lower().split(config["main"]["phrase_separator"])
        actions = []
        for sub_voice_command in sub_voice_commands:
            actions.append(VoiceAction(sub_voice_command))

        self.detectLocations(actions,client_id)

        self.detectPoints(actions)

        self.detectCommand(actions)

        #for action in actions:
        #    for location in action.locations:
        #        self.log.info(u"Location: {}".format(location))
        #    for point in action.points:
        #        self.log.info(u"Location: {}".format(point))

        self.validateActions(actions)

        item_actions = []
        for action in actions:
            item_actions = item_actions + action.item_actions.values()

        return item_actions
 
        #for attribute in semantic_data.item_attributes:
        #    self.log.info(u"{}".format(semantic_data.item_attributes[attribute]))

    def execute(self, module, input):
        voice_command, client_id, fallback_room = self.parseData(input['event'].getItemState().toString())
        self.process(voice_command, client_id, fallback_room)
        
#postUpdate("VoiceCommand","Schalte Licht im Wohnzimmer")
#postUpdate("VoiceCommand","Rollläden im Wohnzimmer hoch und Licht an")
#postUpdate("VoiceCommand","Rollläden im Wohnzimmer und Schlafzimmer hoch")
#postUpdate("VoiceCommand","Schalte Licht im Wohnzimmer an und im Obergeschoss aus")

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