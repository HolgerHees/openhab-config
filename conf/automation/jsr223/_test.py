#from org.eclipse.smarthome.automation import Rule as SmarthomeRule
#from marvin.helper import log, rule
#from core.jsr223 import scope
#from core.triggers import CronTrigger,ItemStateUpdateTrigger 

#SimpleRule = scope.SimpleRule

#log.info(u"{}".format(SimpleRule))

#uid_field = type(SimpleRule).getClass(SimpleRule).getDeclaredField(SimpleRule, "uid")

#@rule("_test.py")
#class EventMonitorRule:
#  def __init__(self):
#    self.triggers = [
#        ItemStateUpdateTrigger("Lights"),
#        CronTrigger("*/15 * * * * ?")
#    ]
  
#  def execute(self, module, input):
#    log.info(u"test executed")



#log.info(u"{}".format(test))

#from marvin.helper import log, rule, getItemState, getItemLastUpdate, itemLastUpdateOlderThen, getNow

#log.info( getItemState("State_Present") )
#log.info( getItemState("roomba_auto") )
#log.info( getItemState("roomba_status") )
#log.info( getItemState("roomba_batPct"))
#log.info( getItemLastUpdate("roomba_cleaning_state") )
#log.info( getItemLastUpdate("State_Present") )

'''if getItemState("State_Present") == OFF \
                and getItemState("roomba_auto") == ON \
                and getItemState("roomba_status").toString() == "Charging" \
                and getItemState("roomba_batPct").intValue() >= 100:
            if itemLastUpdateOlderThen("roomba_cleaning_state", getNow().minusMinutes(360)) \
                    and itemLastUpdateOlderThen("State_Present", getNow().minusMinutes(60)):'''


'''from openhab.triggers import CronTrigger

testTimer = None

@rule("_test.py")
class EventMonitorRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("*/15 * * * * ?")
        ]

    def callback(self):
        log.info("test")

    def execute(self, module, input):
        global testTimer
        if testTimer is not None:
            testTimer.cancel()
            testTimer = None

        testTimer = createTimer(20,self.callback)
        testTimer.start()'''


'''from marvin.helper import log, rule, getItemState
from openhab.triggers import ItemStateUpdateTrigger,CronTrigger
from openhab.jsr223 import scope, get_scope

@rule("_test.py",profile=True)
class EventMonitorRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("*/15 * * * * ?")
        ]

    def execute(self, module, input):
        self.log.info( getItemState("Lights").toString() )
        self.log.info("debug")'''
 

# from marvin.helper import log, logExecution, getItemState, sendCommand, postUpdate
# log.warn("test")


'''from openhab.jsr223.scope import scriptExtension
from org.osgi.framework import FrameworkUtil, ServiceListener, ServiceEvent
from openhab.triggers import ItemStateUpdateTrigger,CronTrigger
from marvin.helper import log, rule

_bundle = FrameworkUtil.getBundle(type(scriptExtension))
bundle_context = _bundle.getBundleContext() if _bundle else None

container = bundle_context.getContainer()
registry = container.getServiceRegistry();

class CustomListener(ServiceListener):
    def serviceChanged( self, event):
        if event.getType() == ServiceEvent.REGISTERED:
            log.info("Trigger registered for topic '" + str(event.getServiceReference().getProperty("event.topics")) + "'" )
        elif event.getType() == ServiceEvent.MODIFIED or event.getType() == ServiceEvent.MODIFIED_ENDMATCH:
            log.info("Trigger modified for topic '" + str(event.getServiceReference().getProperty("event.topics")) + "'" )
        elif event.getType() == ServiceEvent.UNREGISTERING:
            log.info("Trigger unregistered for topic '" + str(event.getServiceReference().getProperty("event.topics")) + "'" )
        else:
            log.info("Service unknown event " + str(event))
            log.info(">>>>serviceChanged " + str(event.getType()) + " " + str(event.getServiceReference().getProperty("event.topics")))
listener = CustomListener()
bundle_context.addServiceListener(listener)

#def scriptLoaded(id):
#    log.info("load")

def scriptUnloaded():
    bundle_context.removeServiceListener(listener)
    log.info("unload")






@rule("_test.py")
class EventMonitorRule:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("Lights"),
            ItemStateUpdateTrigger("Sockets"),
            CronTrigger("15 3/7/243 * * * ?")
        ]

    def execute(self, module, input):
        self.log.info(str(input))'''
        
        
        
        

'''
from org.slf4j import LoggerFactory
from threading import Timer

log = LoggerFactory.getLogger("org.eclipse.smarthome.automation.examples.test")

def callback():
    log.info("callback")
    Timer( 10 , callback).start()

callback()
'''
