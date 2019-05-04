from org.joda.time import DateTime
from org.joda.time.format import DateTimeFormat

from marvin.helper import rule, getNow, getHistoricItemEntry, getHistoricItemState, getItemLastUpdate, getItemState, postUpdate, postUpdateIfChanged
from core.triggers import CronTrigger, ItemStateChangeTrigger

startGasZaehlerStand = 8522.67
startGasZaehlerCounter = 0

dateTimeFormatter = DateTimeFormat.forPattern("yyyy-MM-dd HH:mm:ss.SSS")

def getHistoricReference(log, itemName, valueTime, outdatetTime, messureTime, intervalTime):
    endTime = getItemLastUpdate(itemName)
    endTimestampInMillis = endTime.getMillis()

    nowInMillis = getNow().getMillis()
 
    if endTimestampInMillis < nowInMillis - ( outdatetTime * 1000 ):
        log.info( u"No consumption. Last value is too old." )
        return 0

    minMessuredTimestampInMillis = nowInMillis - ( messureTime * 1000 )

    endValue = getItemState(itemName).doubleValue()

    startTimestampInMillis = endTimestampInMillis
    startValue = 0

    currentTime = DateTime( startTimestampInMillis - 1 )

    itemCount = 0

    while True:
        itemCount = itemCount + 1

        historicEntry = getHistoricItemEntry(itemName, currentTime )

        startValue = historicEntry.getState().doubleValue()

        _millis = historicEntry.getTimestamp().getTime()

        # current item is older then the allowed timeRange
        if _millis < minMessuredTimestampInMillis:
            log.info( u"Consumption time limit exceeded" )
            startTimestampInMillis = startTimestampInMillis - (intervalTime * 1000)
            if _millis > startTimestampInMillis:
                 startTimestampInMillis = _millis
            break
        # 2 items are enough to calculate with
        elif itemCount >= 2:
            log.info( u"Consumption max item count exceeded" )
            startTimestampInMillis = _millis
            break
        else:
            startTimestampInMillis = _millis
            currentTime = DateTime( startTimestampInMillis - 1 )

    durationInSeconds = round(float(endTimestampInMillis - startTimestampInMillis) / 1000.0)
    value = ( (endValue - startValue) / durationInSeconds) * valueTime
    if value < 0:
        value = 0

    if itemName == 'Electricity_Meter':
        display_value = int( round( value * 12 * 1000) )
    else:
        display_value = value

    startTime = DateTime(startTimestampInMillis)
    log.info( u"Consumption {} messured from {} ({}) to {} ({})".format(display_value,startValue,dateTimeFormatter.print(startTime),endValue,dateTimeFormatter.print(endTime)))

    return value


@rule("values_consumption.py")
class SolarPower5minRule:
    def __init__(self):
        self.triggers = [CronTrigger("45 */30 * * * ?")]

    def execute(self, module, input):
        value5Min = getHistoricReference(self.log, "Heating_Solar_Power", 300, 3600, 5600, 1800)
        postUpdateIfChanged("Heating_Solar_Power_Current5Min",value5Min)


'''@rule("values_consumption.py")
class EnergyConsumptionRule2:
    def __init__(self):
        self.triggers = [CronTrigger("*/15 * * * * ?")]

    def execute(self, module, input):'''

referenceCounterDemandValue = 21158037
referenceCounterSupplyValue = 0

@rule("values_consumption.py")
class EnergyCounterDemandRuleTest:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("Energy_Demand")
        ]

    def execute(self, module, input):
        zaehlerStandCurrent = getItemState("Energy_Demand").intValue()
        zaehlerStandTotal = ( referenceCounterDemandValue + zaehlerStandCurrent ) / 1000.0
        postUpdateIfChanged("Test_Electricity_Meter_Demand",zaehlerStandTotal)

@rule("values_consumption.py")
class EnergyCounterSupplyRuleTest:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("Energy_Supply")
        ]

    def execute(self, module, input):
        zaehlerStandCurrent = getItemState("Energy_Supply").intValue()
        zaehlerStandTotal = ( referenceCounterSupplyValue + zaehlerStandCurrent ) / 1000.0
        postUpdateIfChanged("Test_Electricity_Meter_Supply",zaehlerStandTotal)

@rule("values_consumption.py")
class EnergyConsumptionRuleTest:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("Power_Demand"),
          ItemStateChangeTrigger("Power_Supply"),
          ItemStateChangeTrigger("Solar_AC_Power")
    ]

    def execute(self, module, input):
        powerDemand = getItemState("Power_Demand").intValue()
        powerSupply = getItemState("Power_Supply").intValue()
        solarPower = getItemState("Solar_AC_Power").intValue()

        postUpdateIfChanged("Test_Electricity_Current_Consumption",powerDemand - powerSupply + solarPower)
        
        postUpdateIfChanged("Test_Electricity_Current_Demand",powerDemand - powerSupply)
        

@rule("values_consumption.py")
class EnergyConsumptionRule:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("Electricity_Meter"),
          CronTrigger("0 */5 * * * ?")
        ]

    def execute(self, module, input):
        now = getNow()
        zaehlerStandCurrent = getItemState("Electricity_Meter").doubleValue()

        # *** Aktueller Verbrauch ***
        value5Min = getHistoricReference( self.log, "Electricity_Meter", 300, 360, 900, 300 )
        
        # convert kwh to watt/5min
        # mit 12 multiplizieren da Zählerstand in KW pro Stunde ist
        watt5Min = int( round( value5Min * 12 * 1000 ) )

        postUpdateIfChanged("Electricity_Current_Consumption",watt5Min)

        # *** Tagesverbrauch ***
        zaehlerStandOld = getHistoricItemState("Electricity_Meter", now.withTimeAtStartOfDay() ).doubleValue()
        currentConsumption = zaehlerStandCurrent - zaehlerStandOld

        postUpdateIfChanged("Electricity_Current_Daily_Consumption",currentConsumption)

        # *** Jahresverbrauch ***
        zaehlerStandOld = getHistoricItemState("Electricity_Meter", now.withDate(now.getYear()-1, 12, 31 )).doubleValue()
        currentConsumption = zaehlerStandCurrent - zaehlerStandOld

        if postUpdateIfChanged("Electricity_Annual_Consumption", currentConsumption ):
            # Hochrechnung
            zaehlerStandCurrentOneYearBefore = getHistoricItemState("Electricity_Meter", now.minusYears(1) ).doubleValue()
            forecastConsumtion = zaehlerStandOld - zaehlerStandCurrentOneYearBefore

            zaehlerStandOldOneYearBefore = getHistoricItemState("Electricity_Meter", now.withDate(now.getYear()-2, 12, 31 )).doubleValue()

            hochrechnungVerbrauch = int( round( currentConsumption + forecastConsumtion ) )
            vorjahresVerbrauch = int( round( zaehlerStandOld - zaehlerStandOldOneYearBefore ) )
            msg = u"{} KWh, {} KWh".format(hochrechnungVerbrauch,vorjahresVerbrauch)
            postUpdate("Electricity_Forecast", msg )


@rule("values_consumption.py")
class GasConsumptionRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 */5 * * * ?")]

    def execute(self, module, input):
        now = getNow()
        Aktuell_End = getItemState("Gas_Pulse_Counter").doubleValue()

        # Aktueller Zählerstand
        zaehlerStandCurrent = startGasZaehlerStand + ((Aktuell_End - startGasZaehlerCounter) * 0.01)

        zaehlerStandSaved = getItemState("Gas_Current_Count").doubleValue()
        
        #self.log.info(u"{} {}".format(zaehlerStandCurrent,zaehlerStandSaved))

        if zaehlerStandCurrent < zaehlerStandSaved:
            self.log.error("Consumption: Calculation is wrong")
            return

        if zaehlerStandCurrent > zaehlerStandSaved:
            # Aktueller Zählerstand
            postUpdate("Gas_Current_Count", zaehlerStandCurrent )

        # *** Aktueller Verbrauch ***
        value5Min = getHistoricReference( self.log, "Gas_Current_Count", 300, 615, 900, 300 )
        postUpdateIfChanged("Gas_Current_Consumption",value5Min)

        # *** Aktueller Tagesverbrauch ***
        zaehlerStandOld = getHistoricItemState("Gas_Current_Count", now.withTimeAtStartOfDay() ).doubleValue()
        currentConsumption = zaehlerStandCurrent - zaehlerStandOld
        if currentConsumption < 0:
            currentConsumption = 0

        postUpdateIfChanged("Gas_Current_Daily_Consumption",currentConsumption)

        # *** Jahresverbrauch ***
        zaehlerStandOld = getHistoricItemState("Gas_Current_Count", now.withDate(now.getYear()-1, 12, 31 )).doubleValue()
        currentConsumption = zaehlerStandCurrent - zaehlerStandOld
        if currentConsumption < 0:
            currentConsumption = 0

        if postUpdateIfChanged("Gas_Annual_Consumption", currentConsumption ):
            # Hochrechnung
            zaehlerStandCurrentOneYearBefore = getHistoricItemState("Gas_Current_Count", now.minusYears(1) ).doubleValue()
            forecastConsumtion = zaehlerStandOld - zaehlerStandCurrentOneYearBefore

            zaehlerStandOldOneYearBefore = getHistoricItemState("Gas_Current_Count", now.withDate(now.getYear()-2, 12, 31 )).doubleValue()

            hochrechnungVerbrauch = round( currentConsumption + forecastConsumtion )

            msg = u"{} m³, {} m³".format(hochrechnungVerbrauch,int( round( zaehlerStandOld - zaehlerStandOldOneYearBefore ) ))
            postUpdate("Gas_Forecast", msg )
