import time

from org.slf4j import LoggerFactory

# import sys

log = LoggerFactory.getLogger("org.openhab.core.automation")

log.info("jsr223: checking for initialised context")

while True:
    try:
        scriptExtension.importPreset("RuleSupport")
        # from openhab.jsr223.scope import items
        # if items != None:
        if automationManager is not None:
            break;
    except:
        # instance = sys.exc_info()[1]
        # log.info(str(instance))
        pass
    log.info("jsr223: context not initialised yet. waiting 10 sec before checking again")
    time.sleep(10)

log.info("jsr223: done")
