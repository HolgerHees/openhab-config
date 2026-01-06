#from openhab import rule
#from openhab.triggers import ItemScriptCondition, GenericCronTrigger

from scope import cache
import time
from openhab import rule
from openhab.triggers import SystemStartlevelTrigger

counter = 0.2
rate = 3.54409
start_time = time.time_ns()

def run_loop_cache(loops, local_cache, initial, _rate):
  put = local_cache.put
  get = local_cache.get
  put('counter', initial)
  for i in range(loops):
    count = get('counter');
    count = _rate*count*(1 - count);
    put('counter', count);

run_loop_cache(100000, cache.privateCache, counter, rate)

end_time = time.time_ns()
elapsed_time = (end_time - start_time) // 1000000
print(f'Performance Test: Python ran in {elapsed_time} milliseconds')

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
