from custom.heating2.heating import Heating, HeatingLogHelper
from custom.heating2.config import BuildingConfig

class HeatingHelper:
    STATE_MODE_MANUAL = 0
    STATE_MODE_SUSPENDED = 1
    STATE_MODE_HEATING = 2

    OPERATING_MODE_HEATING = 1
    OPERATING_MODE_SUMMER = 3
