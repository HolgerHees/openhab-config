import traceback
import time
import profile, pstats, io
import threading

#from java.util import UUID
#import datetime
from org.eclipse.smarthome.automation import Rule as SmarthomeRule

from org.eclipse.smarthome.model.persistence.extensions import PersistenceExtensions
from org.eclipse.smarthome.core.thing import ChannelUID
from org.joda.time import DateTime

from openhab.actions import Mail, Pushover #, XMPP
from openhab.jsr223 import scope, get_scope, get_automation_manager
from openhab.log import logging
from openhab.triggers import ItemStateUpdateTrigger, ItemStateChangeTrigger

LOG_PREFIX = "org.eclipse.smarthome.automation.custom"
log = logging.getLogger(LOG_PREFIX)

scope.scriptExtension.importPreset("RuleSimple")
scriptExtension = scope.scriptExtension
itemRegistry = scope.itemRegistry
SimpleRule = scope.SimpleRule
things = scope.things
items = scope.items
events = scope.events

scriptExtension.importPreset("RuleSimple")

class rule(object):
    def __init__(self, name,profile=None):
        self.name = name
        self.profile = profile
    def __call__(self, clazz):
        proxy = self
        
        filePackage = proxy.getFilePackage(proxy.name)
        classPackage = proxy.getClassPackage(clazz.__name__)

        def init(self, *args, **kwargs):
            SimpleRule.__init__(self)
            proxy.set_uid_prefix(self,classPackage,filePackage)
            clazz.__init__(self, *args, **kwargs)

            self.triggerItems = {}
            for trigger in self.triggers:
                self.triggerItems[ trigger.getConfiguration().get("itemName") ] = True

        subclass = type(clazz.__name__, (clazz, SimpleRule), dict(__init__=init))
        subclass.execute = proxy.executeWrapper(clazz.execute)
        
        subclass.log = logging.getLogger( LOG_PREFIX + "." + filePackage + "." + classPackage )

        get_automation_manager().addRule(subclass())

        subclass.log.debug("Rule initialised")
        
        return subclass
    
    def getFilePackage(self,fileName):
        if fileName.endswith(".py"):
            filePackage = fileName[:-3]
        else:
            filePackage = fileName

        return filePackage

    def getClassPackage(self,className):
        if className.endswith("Rule"):
            classPackage = className[:-4]
        else:
            classPackage = className
        return classPackage
    
    def set_uid_prefix(self, rule, className, fileName):
        uid_field = type(SmarthomeRule).getClass(SmarthomeRule).getDeclaredField(SmarthomeRule, "uid")
        uid_field.setAccessible(True)
        #uid_field.set(rule, "{}-{}".format(prefix, str(UUID.randomUUID())))
        #st = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        #st = datetime.datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
        #uid_field.set(rule, "{}-{}".format(prefix, st))
        uid_field.set(rule, "{} ({})".format(className, fileName))

    def executeWrapper(self,func):
        proxy = self
        
        def appendDetailInfo(self,event):
            if event is not None:
                if event.getType().startswith("Item"):
                    return " [Item: " + event.getItemName() + "]"
                elif event.getType().startswith("Group"):
                    return " [Group: " + event.getItemName() + "]"
                else:
                    return " [" + event.getType() + " " + str(self) + "]"
            return ""

        def func_wrapper(self, module, input):
            
            try:
                event = input['event']
                # *** Filter indirect events out (like for groups related to the configured item)
                if event.getItemName() not in self.triggerItems:
                    self.log.debug("Rule skipped. Event is not related" + appendDetailInfo(self,event) )
                    return
            except KeyError:
                event = None
            
            try:
                start_time = time.clock()
                
                # *** execute
                if proxy.profile:
                    pr = profile.Profile()

                    #self.log.debug(str(getItem("Lights")))
                    #pr.enable()
                    pr.runctx('func(self, module, input)', {'self': self, 'module': module, 'input': input, 'func': func }, {})              
                    status = None
                else:
                    status = func(self, module, input)

                if proxy.profile:
                    #pr.disable()
                    s = io.BytesIO()
                    #http://www.jython.org/docs/library/profile.html#the-stats-class
                    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
                    ps.print_stats()
                    self.log.debug(s.getvalue())

                if status is None or status is True:
                    elapsed_time = round( ( time.clock() - start_time ) * 1000, 1 )

                    msg = "Rule executed in " + "{:6.1f}".format(elapsed_time) + " ms" + appendDetailInfo(self,event)

                    self.log.debug(msg)
                
            except NotInitialisedException as e:
                self.log.warn("Rule skipped: " + str(e))
            except:
                self.log.error("Rule execution failed:\n" + traceback.format_exc())

        return func_wrapper


class NotInitialisedException(Exception):
    pass


class createTimer:
    def __init__(self,duration, callback, args=[], kwargs={}):
        self.timer = threading.Timer(duration, callback, args, kwargs)
        #log.info(str(self.timer))
        
    def start(self):
        if not self.timer.isAlive():
            #log.info("timer started")
            self.timer.start() 
        else:
            #log.info("timer already started")
            pass
        
    def cancel(self):
        if self.timer.isAlive():
            #log.info("timer stopped")
            self.timer.cancel()
        else:
            #log.info("timer not alive")
            pass



def _getItemName(item):
    if isinstance(item, basestring):
        return item
    else:
        return item.getName()


def _getItem(item):
    if isinstance(item, basestring):
        return getItem(item)
    else:
        return item


# *** Group trigger ***
def _walkRecursive(parent):
    result = []
    items = parent.getAllMembers()
    for item in items:
        if item.getType() == "Group":
            result = result + _walkRecursive(item)
        else:
            result.append(item)
    return result


def getGroupMember(itemOrName):
    return _walkRecursive(_getItem(itemOrName))


#def getGroupMemberUpdateTrigger(itemOrName, state=None, triggerName=None):
#    triggers = []
#    items = _walkRecursive(getItem(itemOrName))
#    for item in items:
#        triggers.append(ItemStateUpdateTrigger(item.getName(), state, triggerName))
#    return triggers


def getGroupMemberChangeTrigger(itemOrName, state=None, triggerName=None):
    triggers = []
    items = getGroupMember(itemOrName)
    for item in items:
        triggers.append(ItemStateChangeTrigger(item.getName(), state, triggerName))
    return triggers


# *** Item getter ***
def getChannel(name):
    item = things.getChannel(ChannelUID(name))
    if item is None:
        raise NotInitialisedException("Channel '" + name + "' not found")
    return item

def getItem(name):
    item = itemRegistry.getItem(name)
    if item is None:
        raise NotInitialisedException("Item '" + name + "' not found")
    return item


def getFilteredChildItems(itemOrName, state):
    items = getGroupMember(itemOrName)
    if isinstance(state, list):
        return filter(lambda child: child.getState() in state, items)
    else:
        return filter(lambda child: child.getState() == state, items)


def getItemState(itemOrName):
    name = _getItemName(itemOrName)
    state = items.get(name)
    if state is None:
        raise NotInitialisedException("Item state for '" + name + "' not found")
    return state


def getHistoricItemEntry(itemOrName, refDate):
    item = _getItem(itemOrName)
    historicEntry = PersistenceExtensions.historicState(item, refDate, "jdbc")
    if historicEntry is None:
        raise NotInitialisedException("Item history for '" + item.getName() + "' not found")
    return historicEntry


def getHistoricItemState(itemOrName, refDate):
    return getHistoricItemEntry(itemOrName, refDate).getState()


def getMaxItemState(itemOrName, refDate):
    item = _getItem(itemOrName)
    historicState = PersistenceExtensions.maximumSince(item, refDate, "jdbc")
    if historicState is None:
        raise NotInitialisedException("Item max state for '" + item.getName() + "' not found")
    return historicState.getState()


# *** Item updates ***
def _checkForUpdates(itemOrName, state):
    if isinstance(state, basestring):
        if getItemState(itemOrName).toString() == state:
            return False
    elif isinstance(state, int):
        if getItemState(itemOrName).doubleValue() == float(state):
            return False
    elif isinstance(state, float):
        if getItemState(itemOrName).doubleValue() == state:
            return False
    elif getItemState(itemOrName) == state:
        return False

    return True

def postUpdateIfChanged(itemOrName, state):
    if not _checkForUpdates(itemOrName, state):
        return False

    postUpdate(itemOrName, state)
    return True


def postUpdate(itemOrName, state):
    item = _getItem(itemOrName)
    return events.postUpdate(item, state)


def sendCommandIfChanged(itemOrName, state):
    if not _checkForUpdates(itemOrName, state):
        return False

    sendCommand(itemOrName, state)
    return True

def sendCommand(itemOrName, command):
    item = _getItem(itemOrName)
    return events.sendCommand(item, command)


# *** DateTime helper ***
def getNow():
    return DateTime.now()


def itemStateNewerThen(itemOrName, refDate):
    return getItemState(itemOrName).calendar.getTimeInMillis() > refDate.getMillis()


def itemStateOlderThen(itemOrName, refDate):
    return not itemStateNewerThen(itemOrName, refDate)


def itemLastUpdateNewerThen(itemOrName, refDate):
    return getItemLastUpdate(itemOrName).isAfter(refDate)


def itemLastUpdateOlderThen(itemOrName, refDate):
    return not itemLastUpdateNewerThen(itemOrName, refDate)


def getItemLastUpdate(itemOrName):
    item = _getItem(itemOrName)
    lastUpdate = PersistenceExtensions.lastUpdate(item)
    if lastUpdate is None:
        raise NotInitialisedException("Item lastUpdate for '" + item.getName() + "' not found")
    return lastUpdate


# *** Notifications and Emails ***
def sendNotification(header, message, url=None):
    Pushover.pushover(header + ": " + message)
    #XMPP.sendXMPP("holger.hees@gmail.com", header + ": " + message)


def sendMail(header, message, url=None):
    Mail.sendMail("holger.hees@gmail.com", header, message, url)
