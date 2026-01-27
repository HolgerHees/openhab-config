#from openhab import rule
#from openhab.triggers import ItemScriptCondition, GenericCronTrigger

from scope import cache
import time
from openhab import rule
from openhab.triggers import SystemStartlevelTrigger

import scope

horizon_slots = [
    { "azimut":   0.00,  "elevation": 30.0,      "factor": 0.5 },   # Nachbar 1 (geradezu)
    { "azimut":  14.00,  "elevation":  8.0,      "factor": 0.1 },
    { "azimut":  24.50,  "elevation": 12.0,      "factor": 0.1 },   # Nachbar 2
    { "azimut":  36.00,  "elevation":  8.0,      "factor": 0.1 },
    { "azimut":  44.00,  "elevation": 12.0,      "factor": 0.1 },   # Nachbar 3
    { "azimut":  52.00,  "elevation":  8.0,      "factor": 0.1 },
    { "azimut":  56.00,  "elevation": 19.2,      "factor": 0.1 },   # Erster Großer Baum
    { "azimut":  65.00,  "elevation":  9.0,      "factor": 0.1 },   # Strasse
    { "azimut":  72.00,  "elevation": 22.0,      "factor": 0.1 },   # Baumreihe bei Fam. Marder
    { "azimut":  86.00,  "elevation": 27.5,      "factor": 0.1 },   # Zweiter Teil der Baumreihe bei Fam. Marder
    { "azimut": -171.00,  "elevation": 10.0,      "factor": 0.1 },
    { "azimut": -168.00,  "elevation": 13.5,      "factor": 0.1 },
    { "azimut": -158.50,  "elevation": 12.5,      "factor": 0.1 },
    { "azimut": -149.50,  "elevation": 10.0,      "factor": 0.1 },
    { "azimut": -144.00,  "elevation":  8.0,      "factor": 0.1 },
    { "azimut": -139.00,  "elevation": 10.0,      "factor": 0.1 },
    { "azimut": -132.50,  "elevation":  8.0,      "factor": 0.1 },
    { "azimut": -118.00,  "elevation": 12.5,      "factor": 0.1 },   # Große Tanne links von Brendel
    { "azimut": -111.00,  "elevation": 10.0,      "factor": 0.1 },   # Nachbar (Brendel)
    { "azimut":  -97.00,  "elevation": 12.5,      "factor": 0.1 },   # Nachbar (hinten)
    { "azimut":  -78.00,  "elevation": 20.0,      "factor": 0.1 },   # Große Tanne hinten rechts
    { "azimut":  -67.00,  "elevation": 12.5,      "factor": 0.1 }
]

for slot in horizon_slots:
    azimut = slot["azimut"]
    if azimut < 0:
        azimut = azimut + 270

    print(azimut, slot["azimut"])

print(scope.actions.get("astro","astro:sun:local").getElevation)

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
