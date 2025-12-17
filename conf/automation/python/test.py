from openhab import rule
from openhab.triggers import ItemScriptCondition, GenericCronTrigger

#@rule(
#    triggers = [
#        GenericCronTrigger("*/5 * * * * ?"),
#    ],
#    conditions = [
#        ItemScriptCondition("""
#def check():
#    return True
#
#check()
#        """)
#    ]
#)
#class Test():
#    def execute(self, module, input):
#        print("Test")


"""from openhab.services import getService
from org.openhab.core.thing import ChannelUID, ThingUID

import scope

def versiontuple(v):
    return tuple(map(lambda part: int(part) if part.isdigit() else 0, (v.split("."))))

BUNDLE_VERSION = versiontuple("5.1.0.M1")

print(BUNDLE_VERSION)


def test(value=1):
    print(value)
    value = value + 1
test()
test()"""



"""try:
    item1 = Registry.getItem("TestChannelItem1")
except:
    item1 = Registry.addItem("TestChannelItem1", "Number")

item1.linkChannel("astro:sun:local:rise#start")

channels = item1.getChannelLinks()
print(channels)

item1.unlinkChannel("astro:sun:local:rise#start")

channels = item1.getChannelLinks()
print(channels)"""
