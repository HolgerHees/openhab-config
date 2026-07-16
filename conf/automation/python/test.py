from openhab.triggers import ItemStateChangeTrigger
from openhab import rule, Registry

from openhab.actions import Voice

import scope

#gemini = scope.actions.get("gemini", "gemini:account:smartserver")

#message = "Test"
#message = "Wie spät ist es jetzt?"
#response = Voice.interpret(message, "gemini", None, "get-date-time,item-get-state,item-send-command")
#response = Voice.interpret("Schalte Licht im Büro aus", "gemini", None, "get-date-time,item-get-state,item-send-command")
#logger.info(response)


test = Registry.getItem("pFF_Bedroom_Air_Sensor_Temperature_Value").getState()
print(test)

test = Registry.getItem("pFF_Bedroom_Heating_Temperature_Target").getState()
print(test)

#var.test = 1



#@rule(
#    triggers = [
#        ItemStateChangeTrigger("TestItem"),
#    ]
#)
#class TabletScreen:
#    def execute(self, module, input):
#        print(input["event"])

#scope.events.postUpdate(Registry.getItem("TestItem"), 2, None)

#print(Registry.getItem("pOutdoor_Astro_Sun_Azimuth").getChannels())
#print(Registry.getItem("pOutdoor_Astro_Sun_Azimuth").getChannelsNeu())



