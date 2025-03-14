import java
from openhab import logger
from openhab.actions import Transformation

mode = Transformation.transform("PY3", "test.py", "xyz" )
print(mode)



from org.openhab.core import OpenHAB

logger.info(java.type("org.openhab.core.OpenHAB").getVersion())
logger.info(OpenHAB.getVersion())

logger.info(str(globals().keys()))




