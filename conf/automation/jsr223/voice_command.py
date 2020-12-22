from shared.helper import rule, postUpdate, sendCommandIfChanged, getItemState

from core.triggers import ItemStateUpdateTrigger

from alexa.device_config import AlexaDevices

from alexa.semantic_config import SemanticConfig

from alexa.semantic_model import SemanticModel

from alexa.semantic_test import Cases

import re
import traceback
   
class VoiceAction:
    def __init__(self,cmd):
        self.cmd_complete = cmd
        self.unprocessed_search = cmd
        
        self.locations = []
        self.location_search_terms = []
        
        self.points = []
        self.point_search_terms = []

        self.cmd = None
        self.cmd_search_terms = []
        
        self.item_actions = []

class ItemCommand:
    def __init__(self,cmd_config,cmd_name,cmd_argument):
        self.cmd_config = cmd_config
        self.cmd_name = cmd_name
        self.cmd_argument = cmd_argument

class ItemAction:
    def __init__(self,item,cmd_name,cmd_argument):
        self.item = item
        self.cmd_name = cmd_name
        self.cmd_argument = cmd_argument

class ItemMatcher:
    def __init__(self,semantic_item,full_match,part_match):
        self.semantic_item = semantic_item
        self.full_match = []
        for match in full_match:
            self.full_match += match.split(" ")
        #self.part_match = part_match
        self.part_match = []
        for match in part_match:
            self.part_match += match.split(" ")
    
    def getPriority(self):
        return len(self.full_match) * 1.2 + len(self.part_match) * 1.1
        #return len(" ".join(self.full_match)) * 1.2 + len(" ".join(self.part_match)) * 1.1
 
@rule("voice_command.py")
class VoiceCommandRule:
    def __init__(self):
        self.triggers = [ ItemStateUpdateTrigger("VoiceCommand") ]

        self.semantic_model = SemanticModel(ir,SemanticConfig)
        self.semantic_model.test(self.log)
        
        self.full_phrase_map, self.full_phrase_terms = self.buildSearchMap(self.semantic_model.getSemanticItem(SemanticConfig["main"]["phrase_equipment"]).getChildren())
 
    def buildSearchMap(self,semantic_items):
        search_map = {}
        for semantic_item in semantic_items:
            for search_term in semantic_item.getSearchTerms():
                if search_term not in search_map:
                    search_map[search_term] = []
                search_map[search_term].append(semantic_item)
        search_terms = sorted(search_map, key=len, reverse=True)
        return search_map, search_terms
   
    def getItemsByType(self,parent,type):
        result = []
        if parent.getItem().getType() == "Group":
            #self.log.info(u" => {} {}".format(parent.getName(),parent.getType()))
            items = parent.getItem().getMembers()
            for item in items:
                semantic_item = self.semantic_model.getSemanticItem(item.getName())
                #self.log.info(u" => {}".format(item.getName()))
                if semantic_item.getSemanticType() == type:
                    result.append(semantic_item)
                else:
                    result = result + self.getItemsByType(semantic_item,type)
        return result

    def _searchItems(self,semantic_item,unprocessed_search,items_to_skip,_full_matched_terms,_part_matched_terms,_processed_items):

        matches = []

        if semantic_item in items_to_skip or semantic_item in _processed_items:
            return matches

        _processed_items.append(semantic_item)

        new_matched_terms = []
        full_matched_terms = _full_matched_terms[:]
        part_matched_terms = _part_matched_terms[:]
  
        # check for matches
        is_match = False
        for search_term in semantic_item.getSearchTerms():
            if self.semantic_model.getSearchFullRegex(search_term).match(unprocessed_search):
                full_matched_terms.append(search_term)
                new_matched_terms.append(search_term)
                is_match = True
            elif self.semantic_model.getSearchPartRegex(search_term).match(unprocessed_search):
                part_matched_terms.append(search_term)
                new_matched_terms.append(search_term)
                is_match = True

        # check if matches are just sub phrases
        # => phrases which never works alone
        total_matched_terms = full_matched_terms + part_matched_terms
        if  len(total_matched_terms) == 1 and total_matched_terms[0] in SemanticConfig["main"]["phrase_sub"]:
            full_matched_terms = part_matched_terms = total_matched_terms = new_matched_terms = []
            is_match = False

        # clean unprocessed search terms    
        for search_term in new_matched_terms:
            unprocessed_search = unprocessed_search.replace(search_term,"")

        # check sub elements
        if semantic_item.getItem().getType() == "Group":
            for _item in semantic_item.getItem().getMembers():
                _semantic_item = self.semantic_model.getSemanticItem(_item.getName())
                if _semantic_item.getSemanticType() != semantic_item.getSemanticType():
                    continue
                matches += self._searchItems(_semantic_item,unprocessed_search,items_to_skip,full_matched_terms,part_matched_terms,_processed_items)

        # add own match only if there are no sub matches
        if is_match and len(matches) == 0:
            matches.append(ItemMatcher(semantic_item,list(set(full_matched_terms)),list(set(part_matched_terms))))
    
        return matches

    def searchItems(self,semantic_items,unprocessed_search,items_to_skip=[]):
        matches = []
        for semantic_item in semantic_items:
            _matches = self._searchItems(semantic_item,unprocessed_search,items_to_skip,_full_matched_terms=[],_part_matched_terms=[],_processed_items=[])
            matches += _matches

        # get only matches with highest priority
        final_priority = 0
        final_matches = []
        for match in matches:
            priority = match.getPriority()
            if priority == final_priority:
                final_matches.append(match)
            elif priority > final_priority:
                final_priority = priority
                final_matches = [match]
 
        # collect matched items, search terms and check if they are unique
        matched_items = []
        matched_searches = []
        if len(final_matches) > 0:

            final_items = set(map(lambda match: match.semantic_item.getItem().getName(), final_matches))
            possible_duplicate_search_items = self.semantic_model.getDuplicateSearchItems(final_matches[0].semantic_item.getSemanticType())
                     
            for match in final_matches:

                search_terms = match.full_match + match.part_match

                # filter locations (or equipments), if they match a "special" search term which is also used for an equipments (or points)
                # and the location from this equipment is also part of the matches
                diff = set(search_terms) & set(possible_duplicate_search_items.keys())
                is_allowed = True
                for search_term in diff:
                    #self.log.info(u"{}".format(diff))
                    # check if the equipment parent is also part of matches.
                    # if yes, we can skip the current item
                    if final_items & set(possible_duplicate_search_items[search_term]):
                        #self.log.info(u"{}".format(search_term))
                        #self.log.info(u"{}".format(final_items))
                        #self.log.info(u"{}".format(possible_duplicate_search_items[search_term]))
                        is_allowed = False
                        break

                if not is_allowed:
                    continue 
                
                #    self.log.info(u"{} {}".format(search_term,map[search_term]))
                matched_items.append(match.semantic_item)
                matched_searches += search_terms
            matched_items = list(set(matched_items))
            matched_searches = list(set(matched_searches))
            for matched_search in matched_searches:
                unprocessed_search = unprocessed_search.replace(matched_search,"")
 
        return matched_items,matched_searches,unprocessed_search
    
    def detectLocations(self,actions):
        for action in actions:
            matched_locations, matched_searches, unprocessed_search = self.searchItems(self.semantic_model.getRootLocations(),action.unprocessed_search,[])
            action.unprocessed_search = unprocessed_search

            #if len(matched_locations) > 1:
            #    self.log.info(u"{}".format(action.unprocessed_search))
            #    for location in matched_locations:
            #        self.log.info(u"{}".format(location.getItem().getName()))

            action.locations = matched_locations
            action.location_search_terms = matched_searches
            

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
                action.locations = [ self.semantic_model.getSemanticItem(fallback_location_name) ]
    
    def checkPoints(self,action,unprocessed_search,items_to_skip):
        #self.log.info(u"checkPoints")
        equipments = []
        for location in action.locations:
            # search for equipments    
            #self.log.info(u"  location: '{}', unprocessed_search: '{}'".format(location,unprocessed_search))
            equipments += self.getItemsByType(location,"Equipment")

        matched_equipments, matched_equipment_searches, unprocessed_search = self.searchItems(equipments,unprocessed_search,items_to_skip)
  
        # check points of equipments 
        if len(matched_equipments) > 0:
            points = []
            #point_matches = False
            #processed_search_terms = []
            for equipment in matched_equipments:
                #self.log.info(u"  equipment: '{}', unprocessed_search: '{}'".format(equipment.item.getName(),unprocessed_search))
                points += self.getItemsByType(equipment,"Point")

            matched_points, matched_point_searches, unprocessed_search = self.searchItems(points,unprocessed_search,items_to_skip)

            # add matched points or all equipment points if there are no matches
            if len(matched_points) == 0:
                action.points = points
                action.point_search_terms = matched_equipment_searches
            else:
                action.points = matched_points
                action.point_search_terms = matched_point_searches + matched_equipment_searches
            
            return unprocessed_search

        # check points of locations
        points = []
        for location in action.locations:
            points += self.getItemsByType(location,"Point")

        matched_points, matched_searches, unprocessed_search = self.searchItems(points,unprocessed_search,items_to_skip)
        action.points = matched_points
        action.point_search_terms = matched_searches

        return unprocessed_search 
 
    def detectPoints(self,actions):
        for action in actions:
            # search for points based on voice_cmd
            unprocessed_search = self.checkPoints(action,action.unprocessed_search,[])
            if unprocessed_search != None:
                action.unprocessed_search = unprocessed_search

    def fillPointFallbacks(self,actions):
        # Fill missing points backward until command is found
        last_action = None
        for action in reversed(actions):
            if action.cmd != None: # maybe not needed
                last_action = None
 
            if len(action.points) == 0:
                if last_action != None:
                    self.checkPoints(action,u"{} {}".format(" ".join(last_action.point_search_terms),action.unprocessed_search),last_action.points)
            else:
                last_action = action
 
        # Fill missing points forwards
        last_action = None
        for action in actions:
            # if no points where found search again based on the last cmd with points
            if len(action.points) == 0:
                if last_action != None:
                    self.checkPoints(action,u"{} {}".format(" ".join(last_action.point_search_terms),action.unprocessed_search),last_action.points)
            else:
                last_action = action
 
    def checkCommand(self,action):
        #self.log.info(u"{}".format(action.points))

        for cmd in SemanticConfig["commands"]:
            for search in SemanticConfig["commands"][cmd]["search"]:
                if search[0:1] == "/" and search[-1:] == "/":
                    #self.log.info(u"{} {}".format(search[1:-1],action.unprocessed_search))
                    match = re.match(search[1:-1],action.unprocessed_search)
                    if match:
                        number = match.group(1)
                        if number in SemanticConfig["main"]["number_mapping"]:
                            number = SemanticConfig["main"]["number_mapping"][number]
                        if number.isnumeric():
                            action.cmd_search_terms.append(number)
                            return cmd, SemanticConfig["commands"][cmd], number
                        return None, None, None
                else:
                    parts = action.unprocessed_search.split(" ")
                    if search in parts:
                        action.cmd_search_terms.append(search)
                        return cmd, SemanticConfig["commands"][cmd], None
        return None, None, None
    
    def detectCommand(self,actions):
        for action in actions:
            # search for cmd based on voice_cmd
            cmd_name, cmd_config, cmd_argument = self.checkCommand(action)
            if cmd_name is not None:
                action.cmd = ItemCommand(cmd_config,cmd_name,cmd_argument)


    def fillCommandFallbacks(self,actions):
        # Fill missing commands backward
        last_action = None
        for action in reversed(actions):
            if action.cmd is None:
                if last_action != None:
                    action.cmd = last_action.cmd
            else:
                last_action = action

        # Fill missing commands forward
        last_action = None
        for action in actions:
            # if no cmd found use the last one
            if action.cmd is None:
                if last_action != None:
                    action.cmd = last_action.cmd
            else:
                last_action = action

    def validateActions(self,actions):
        processed_items = {}
        for action in actions:
            for point in action.points:
                item_name = point.item.getName()
                #self.log.info(u"{}".format(item_name))
                if item_name in processed_items \
                    or action.cmd is None \
                    or ( "types" in action.cmd.cmd_config and point.item.getType() not in action.cmd.cmd_config["types"] ) \
                    or ( "tags" in action.cmd.cmd_config and len(filter(lambda x: x in action.cmd.cmd_config["tags"], point.item.getTags()))==0  ):
                    continue
                processed_items[item_name] = True
                action.item_actions.append(ItemAction(point.item,action.cmd.cmd_name,action.cmd.cmd_argument))
        #self.log.info(u"{}".format(processed_items.keys()))
    
    def process(self,voice_command, fallback_location_name):
        actions = []
        voice_command = voice_command.lower()

        # check for full text phrases
        for search in self.full_phrase_terms:
            if search == voice_command:
                action = VoiceAction(search)
                for semantic_item in self.full_phrase_map[search]:
                    action.item_actions.append(ItemAction(semantic_item.getItem(),"ON",None))
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

            self.fillPointFallbacks(actions) # depends on detected commands

            self.fillCommandFallbacks(actions)

            self.validateActions(actions)
 
        return actions

    def getFormattedValue(self,item):
        value = getItemState(item).toString()
        if item.getType() == "Dimmer":
            if value == "0":
                value = SemanticConfig["states"]["OFF"]
            elif value == "100":
                value = SemanticConfig["states"]["ON"]
            else:
                value = u"{} %".format(value)
        elif item.getType() == "Rollershutter":
            if value == "0":
                value = SemanticConfig["states"]["UP"]
            elif value == "100":
                value = SemanticConfig["states"]["DOWN"]
            else:
                value = u"{} %".format(value)
        if value in SemanticConfig["states"]:
            value = SemanticConfig["states"][value]
        return value

    def getParentByType(self,semantic_item,type):
        for parent in semantic_item.getParents():
            if parent.type == "Group":
                continue
            if parent.type == type:
                return parent
            return self.getParentByType(parent,type)

    def getAnswer(self,item):
        semantic_item = self.semantic_model.getSemanticItem(item.getName())
        semantic_equipment = self.getParentByType(semantic_item,"Equipment")
        semantic_location = self.getParentByType(semantic_equipment,"Location")
        #semantic_location = self.getParentByType(semantic_item,"Location")
 
        value = self.getFormattedValue(item)
        
        for tag in item.getTags():
            if tag not in SemanticConfig["answers"]:
                continue
            return SemanticConfig["answers"][tag].format(room=semantic_location.item.getLabel(),state=value)

        semantic_reference = semantic_equipment if len(semantic_equipment.getChildren()) == 1 else semantic_item

        return SemanticConfig["answers"]["Default"].format(equipment=semantic_reference.getItem().getLabel(),room=semantic_location.getItem().getLabel(),state=value)

    def applyActions(self,actions,voice_command,dry_run):
        missing_locations = []
        missing_points = []
        missing_cmds = []
        unsupported_cmds = []
        for action in actions:
            if len(action.item_actions) > 0:
                continue

            if len(action.locations) == 0:
                missing_locations.append(action.unprocessed_search)
            elif len(action.points) == 0:
                missing_points.append(action.unprocessed_search)
            elif action.cmd is None:
                missing_cmds.append(action.unprocessed_search)
            else:
                unsupported_cmds.append(action.unprocessed_search)

        is_valid = False
        join_separator = SemanticConfig["i18n"]["message_join_separator"]
        if len(actions) == len(missing_locations):
            msg = SemanticConfig["i18n"]["nothing_found"].format(term=voice_command)
        elif len(missing_locations) > 0:
            msg = SemanticConfig["i18n"]["nothing_found"].format(term=join_separator.join(missing_locations))
        elif len(missing_points) > 0:
            msg = SemanticConfig["i18n"]["no_equipment_found_in_phrase"].format(term=join_separator.join(missing_points))
        elif len(missing_cmds) > 0:
            msg = SemanticConfig["i18n"]["no_cmd_found_in_phrase"].format(term=join_separator.join(missing_cmds))
        elif len(unsupported_cmds) > 0:
            msg = SemanticConfig["i18n"]["no_supported_cmd_in_phrase"].format(term=join_separator.join(unsupported_cmds))
        else:
            msg = SemanticConfig["i18n"]["ok_message"]
            is_valid = True

        if is_valid:
            msg_r = []
            for action in actions:
                for item_action in action.item_actions:
                    if item_action.cmd_name == "READ":
                        msg_r.append(self.getAnswer(item_action.item))
                        #answer_data.append([item_action.item,value])
                    elif not dry_run:
                        if item_action.cmd_name == "PERCENT":
                            sendCommandIfChanged(item_action.item,item_action.cmd_argument)
                        else:
                            #self.log.info(u"postUpdate {} {}".format(item_action.item.getName(),item_action.cmd_name))
                            sendCommandIfChanged(item_action.item,item_action.cmd_name)
            if len(msg_r) > 0:
                if len(msg_r) > 2:
                    msg_r = [ msg_r[0], SemanticConfig["i18n"]["more_results"].format(count=len(msg_r)-1) ]

                msg = SemanticConfig["i18n"]["message_join_separator"].join(msg_r)
 
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
                        if item_action.item.getName() == case_item and item_action.cmd_name == case_cmd:
                            item_actions_applied.append(item_action)
                            item_actions_skipped.remove(item_action)
                            case_actions_excpected.remove(case_action)

            excpected_result = case["is_valid"] == is_valid if "is_valid" in case else is_valid
    
            location_names = list(set(location_names))
            if len(location_names) > 0 and case.get("location_count",1) != len(location_names):
                for action in actions:
                    for location in action.locations:
                        self.log.info(u"  location: {}".format(location.getItem().getName()))
                excpected_result = False
              
            if excpected_result \
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