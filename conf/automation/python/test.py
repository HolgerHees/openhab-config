from openhab import logger
from openhab.services import get_service

import locale

LOCATION_PROVIDER = get_service("org.openhab.core.i18n.LocaleProvider")

#logger.info(str(LOCATION_PROVIDER.getLocale().toLanguageTag().replace("-","_")))

#locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

logger.info(str(locale.getlocale()[0].split("_")[0]))
