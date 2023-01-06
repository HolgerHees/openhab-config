from shared.helper import rule, getHistoricItemEntry, getHistoricItemState, getItemLastChange, itemLastUpdateOlderThen, itemLastChangeOlderThen, getItemState, getItemStateWithFallback, postUpdate, postUpdateIfChanged, sendCommand
from shared.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger

from java.time import ZonedDateTime
from java.time.format import DateTimeFormatter
from java.time.temporal import ChronoUnit

from org.openhab.core.types.RefreshType import REFRESH
  

totalSupply = 3600 # total possible photovoltaic power in watt
maxTimeSlot = 300000 # value timeslot to messure average power consumption => 5 min

# offset values for total energy demand and supply (total values at the time when knx based energy meter was installed)
startEnergyTotalDemandValue = 21158.037
startEnergyTotalSupplyValue = -90.636

# offset values for electricity meter demand and supply (total values at the time when new electricity meter was changed)
startElectricityMeterDemandValue = 21830.135
startElectricityMeterSupplyValue = 52.75

# offset values for gas meter (total value at the time when knx based impulse counter was resettet)
startGasMeterValue = 10405.39
startGasImpulseCounter = 0

dateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS")

#value = getHistoricItemState("pGF_Utilityroom_Electricity_Current_Daily_Demand",ZonedDateTime.now()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_Current_Daily_Demand",value)
#value = getHistoricItemState("pGF_Utilityroom_Electricity_Current_Daily_Supply",ZonedDateTime.now()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_Current_Daily_Supply",value)
#value = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Supply",ZonedDateTime.now()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_Total_Supply",value)
#value = getHistoricItemState("pGF_Garage_Solar_Inverter_Power_Limitation",ZonedDateTime.now()).intValue()
#postUpdate("pGF_Garage_Solar_Inverter_Power_Limitation",value)

def getHistoricReference(log, itemName, valueTime, outdatetTime, messureTime, intervalTime):
    endTime = getItemLastChange(itemName)

    now = ZonedDateTime.now()
 
    if endTime.isBefore( now.minusSeconds(outdatetTime) ):
        log.info( u"No consumption. Last value is too old." )
        return 0

    minMessuredTime = now.minusSeconds( messureTime )

    endValue = getItemState(itemName).doubleValue()

    startTime = endTime
    startValue = 0

    currentTime = startTime.minusNanos(1)

    itemCount = 0

    while True:
        itemCount = itemCount + 1

        historicEntry = getHistoricItemEntry(itemName, currentTime )

        startValue = historicEntry.getState().doubleValue()

        _time = historicEntry.getTimestamp()

        # current item is older then the allowed timeRange
        if _time.isBefore(minMessuredTime):
            log.info( u"Consumption time limit exceeded" )
            startTime = startTime.minusSeconds(intervalTime)
            if _time.isAfter(startTime):
                 startTime = _time
            break
        # 2 items are enough to calculate with
        elif itemCount >= 2:
            log.info( u"Consumption max item count exceeded" )
            startTime = _time
            break
        else:
            startTime = _time
            currentTime = startTime.minusNanos(1)
            
    durationInSeconds = ChronoUnit.SECONDS.between(startTime,endTime)
    value = ( (endValue - startValue) / durationInSeconds) * valueTime
    if value < 0:
        value = 0

    log.info( u"Consumption {} messured from {} ({}) to {} ({})".format(value,startValue,dateTimeFormatter.format(startTime),endValue,dateTimeFormatter.format(endTime)))

    return value

@rule("values_consumption.py")
class SolarPower5minRule:
    def __init__(self):
        self.triggers = [CronTrigger("45 */30 * * * ?")]

    def execute(self, module, input):
        value5Min = getHistoricReference(self.log, "pGF_Utilityroom_Heating_Solar_Power", 300, 3600, 5600, 1800)
        postUpdateIfChanged("pGF_Utilityroom_Heating_Solar_Power_Current5Min",value5Min)


@rule("values_consumption.py")
class EnergyCounterDemandRule:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("pGF_Utilityroom_Energy_Demand_Active"),
          CronTrigger("1 0 0 * * ?")
        ]

    def execute(self, module, input):
        now = ZonedDateTime.now()
        
        demandCurrent = getItemState("pGF_Utilityroom_Energy_Demand_Active").intValue() / 1000.0
        zaehlerStandCurrent = ( startEnergyTotalDemandValue + demandCurrent )
        postUpdateIfChanged("pGF_Utilityroom_Electricity_Total_Demand",zaehlerStandCurrent)
        
        postUpdateIfChanged("pGF_Utilityroom_Electricity_Meter_Demand",zaehlerStandCurrent-startElectricityMeterDemandValue)

        # *** Tagesbezug ***
        zaehlerStandOld = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Demand", now.toLocalDate().atStartOfDay(now.getZone()) ).doubleValue()
        currentDemand = zaehlerStandCurrent - zaehlerStandOld
        
        postUpdateIfChanged("pGF_Utilityroom_Electricity_Current_Daily_Demand",currentDemand)

        # *** Jahresbezug ***
        refDay = now.withYear(now.getYear()).withMonth(1).withDayOfMonth(1)
        zaehlerStandOld = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Demand", refDay.toLocalDate().atStartOfDay(refDay.getZone())).doubleValue()
        currentDemand = zaehlerStandCurrent - zaehlerStandOld

        if postUpdateIfChanged("pGF_Utilityroom_Electricity_Current_Annual_Demand", currentDemand ):
            # Hochrechnung
            zaehlerStandCurrentOneYearBefore = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Demand", now.minusYears(1) ).doubleValue()
            forecastDemand = zaehlerStandOld - zaehlerStandCurrentOneYearBefore

            refDay = now.withYear(now.getYear()-1).withMonth(1).withDayOfMonth(1)
            zaehlerStandOldOneYearBefore = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Demand", refDay.toLocalDate().atStartOfDay(refDay.getZone())).doubleValue()

            hochrechnungDemand = int( round( currentDemand + forecastDemand ) )
            vorjahresDemand = int( round( zaehlerStandOld - zaehlerStandOldOneYearBefore ) )
            msg = u"{} kWh, {} kWh".format(hochrechnungDemand,vorjahresDemand)
            postUpdate("pGF_Utilityroom_Electricity_Current_Annual_Demand_Forecast", msg )


@rule("values_consumption.py")
class EnergyCounterSupplyRule:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("pGF_Utilityroom_Energy_Supply_Active"),
          CronTrigger("1 0 0 * * ?")
        ]

    def execute(self, module, input):
        now = ZonedDateTime.now()
        
        supplyCurrent = getItemState("pGF_Utilityroom_Energy_Supply_Active").intValue() / 1000.0
        zaehlerStandCurrent = ( startEnergyTotalSupplyValue + supplyCurrent )
        postUpdateIfChanged("pGF_Utilityroom_Electricity_Total_Supply",zaehlerStandCurrent)

        postUpdateIfChanged("pGF_Utilityroom_Electricity_Meter_Supply",zaehlerStandCurrent-startElectricityMeterSupplyValue)

        # *** Tageslieferung ***
        zaehlerStandOld = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Supply", now.toLocalDate().atStartOfDay(now.getZone()) ).doubleValue()
        currentSupply = zaehlerStandCurrent - zaehlerStandOld

        postUpdateIfChanged("pGF_Utilityroom_Electricity_Current_Daily_Supply",currentSupply)
        # *** Jahreslieferung ***
        
        refDay = now.withYear(now.getYear()).withMonth(1).withDayOfMonth(1)
        zaehlerStandOld = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Supply", refDay.toLocalDate().atStartOfDay(refDay.getZone())).doubleValue()
        currentSupply = zaehlerStandCurrent - zaehlerStandOld

        if postUpdateIfChanged("pGF_Utilityroom_Electricity_Current_Annual_Supply", currentSupply ):
            # Hochrechnung
            zaehlerStandCurrentOneYearBefore = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Supply", now.minusYears(1) ).doubleValue()
            forecastSupply = zaehlerStandOld - zaehlerStandCurrentOneYearBefore

            refDay = now.withYear(now.getYear()-1).withMonth(1).withDayOfMonth(1)
            zaehlerStandOldOneYearBefore = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Supply", refDay.toLocalDate().atStartOfDay(refDay.getZone())).doubleValue()

            hochrechnungSupply = int( round( currentSupply + forecastSupply ) )
            vorjahresSupply = int( round( zaehlerStandOld - zaehlerStandOldOneYearBefore ) )
            msg = u"{}kWh, {} kWh".format(hochrechnungSupply,vorjahresSupply)
            postUpdate("pGF_Utilityroom_Electricity_Current_Annual_Supply_Forecast", msg )


'''@rule("values_consumption.py")
class EnergySupplyRule:
    def __init__(self):
        self.triggers = [
          #ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Current_Consumption"),
          #CronTrigger("0 */5 * * * ?")
        ]

        self.stack = []
        self.lastLimitationIncrease = ZonedDateTime.now()

        postUpdate("pGF_Garage_Solar_Inverter_Power_Limitation",100)
        
    def getAvgConsumption(self,now,value):        
        if len(self.stack) > 0:
            avgValue = 0
            currentTime = now
            currentTimeSlot = 0
                  
            for index, x in enumerate( reversed(self.stack) ):           
                
                # remove values older then 5 minutes
                if currentTimeSlot >= maxTimeSlot and len(self.stack) > index:
                    #self.log.info(u"remove samples after index {}".format(len(self.stack)-index))
                    self.stack = self.stack[len(self.stack)-index:]
                    break;

                avgValue += x[0] * ChronoUnit.MILLIS.between(x[1],currentTime)
                currentTime = x[1]
                currentTimeSlot = ChronoUnit.MILLIS.between(currentTime,now)
                  
            avgValue = avgValue / ChronoUnit.MILLIS.between(currentTime,now)
        else:
            avgValue = value

        self.stack.append( [value, now ] )
        
        return avgValue
        
    def getPossibleLimitation(self,consumptionValue):
        currentPercentage = consumptionValue * 100.0 / totalSupply
        possiblePowerLimitation = int( round( 70.0 + currentPercentage ) )
        if possiblePowerLimitation > 100:
            possiblePowerLimitation = 100
        elif possiblePowerLimitation < 70:
            possiblePowerLimitation = 70
            self.log.warn(u"Possible limitation below 70% should never happen. In this case it was {}%".format(possiblePowerLimitation))
        return possiblePowerLimitation

    def execute(self, module, input):
      
        now = ZonedDateTime.now()
        
        currentACPower = getItemState("pGF_Garage_Solar_Inverter_AC_Power").intValue()

        currentPowerLimitation = getItemStateWithFallback("pGF_Garage_Solar_Inverter_Power_Limitation",DecimalType(0)).intValue()
            
        currentConsumptionValue = getItemState("pGF_Utilityroom_Electricity_Current_Consumption").intValue()
        # must be called to fill history stack
        avgConsumptionValue = self.getAvgConsumption(now,currentConsumptionValue)
        
        if currentACPower > 0:
            possiblePowerLimitation = self.getPossibleLimitation(currentConsumptionValue)
            possibleAvgPowerLimitation = self.getPossibleLimitation(avgConsumptionValue)
            
            self.log.info(u"currentLimit: {}%, currentConsumption: {}W, avgConsumption: {}W, possibleLimit: {}%, possibleAvgLimit: {}%, stack: {}, li: {}".format(currentPowerLimitation,currentConsumptionValue,avgConsumptionValue,possiblePowerLimitation,possibleAvgPowerLimitation,len(self.stack),ChronoUnit.MILLIS.between(self.lastLimitationIncrease,now)))

            if possiblePowerLimitation >= currentPowerLimitation:
                self.lastLimitationIncrease = now
                if possiblePowerLimitation > currentPowerLimitation:
                    sendCommand("pGF_Garage_Solar_Inverter_Power_Limitation",possiblePowerLimitation)
                    self.log.info(u"Increase power limitation from {}% to {}%".format( currentPowerLimitation, possiblePowerLimitation ))
                    return
            elif ChronoUnit.MILLIS.between(self.lastLimitationIncrease,now) > maxTimeSlot:
                if possibleAvgPowerLimitation < currentPowerLimitation:
                    sendCommand("pGF_Garage_Solar_Inverter_Power_Limitation",possibleAvgPowerLimitation)
                    self.log.info(u"Decrease power limitation from {}% to {}%".format( currentPowerLimitation, possibleAvgPowerLimitation ))
                    return
                
            if len(input) == 0 and itemLastChangeOlderThen("pGF_Garage_Solar_Inverter_Power_Limitation",ZonedDateTime.now().minusMinutes(4)):
                sendCommand("pGF_Garage_Solar_Inverter_Power_Limitation",currentPowerLimitation)
                self.log.info(u"Refresh power limitation of {}%".format( currentPowerLimitation ))
        elif currentPowerLimitation != 100:
            postUpdate("pGF_Garage_Solar_Inverter_Power_Limitation",100)
            self.log.info(u"Shutdown power limitation")'''

@rule("values_consumption.py")
class EnergyTotalYieldRefreshRule:
    def __init__(self):
        self.triggers = [
          CronTrigger("0 * * * * ?")
        ]
        
    def execute(self, module, input):
        if getItemState("pOther_Automatic_State_Solar") == ON:
            # triggers solar value update
            sendCommand("pGF_Garage_Solar_Inverter_Total_Yield",REFRESH)
        
@rule("values_consumption.py")
class EnergyCurrentDemandAndConsumptionRule:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("pGF_Utilityroom_Power_Demand_Active"),
          ItemStateChangeTrigger("pGF_Utilityroom_Power_Supply_Active"),
          ItemStateUpdateTrigger("pGF_Garage_Solar_Inverter_AC_Power")
        ]
        
    def updateConsumption(self,solarPower):
        consumption = self.currentDemand + solarPower
        
        if consumption > 0:
            postUpdateIfChanged("pGF_Utilityroom_Electricity_Current_Consumption",consumption)
        else:
            self.log.info(u"Skip consumption update. powerDemand: {}, powerSupply: {}, solarPower: {}".format(self.powerDemand,self.powerSupply,solarPower))

    def execute(self, module, input):
        if input["event"].getItemName() == "pGF_Garage_Solar_Inverter_AC_Power":
            self.updateConsumption(input['event'].getItemState().intValue())
        else:
            if input["event"].getItemName() == "pGF_Utilityroom_Power_Demand_Active":
                self.powerDemand = input["event"].getItemState().intValue()
                self.powerSupply = getItemState("pGF_Utilityroom_Power_Supply_Active").intValue()
                
                if self.powerDemand != getItemState("pGF_Utilityroom_Power_Demand_Active").intValue():
                    self.log.error("Item demand state differences: {}, item state: {}".format(self.powerDemand,getItemState("pGF_Utilityroom_Power_Demand_Active").intValue()))
            else:
                self.powerDemand = getItemState("pGF_Utilityroom_Power_Demand_Active").intValue()
                self.powerSupply = input["event"].getItemState().intValue()
                
                if self.powerSupply != getItemState("pGF_Utilityroom_Power_Supply_Active").intValue():
                    self.log.error("Item supply state differences: {}, item state: {}".format(self.powerSupply,getItemState("pGF_Utilityroom_Power_Supply_Active").intValue()))

            self.currentDemand = self.powerDemand - self.powerSupply
            
            #self.log.info(u"{}".format(itemLastUpdateOlderThen("pGF_Garage_Solar_Inverter_Total_Yield", ZonedDateTime.now().minusMinutes(15))))
            
            if getItemState("pOther_Automatic_State_Solar") == ON:
                if itemLastUpdateOlderThen("pOther_Automatic_State_Solar", ZonedDateTime.now().minusMinutes(60)):
                    # solar value update was not successful for a while
                    #solarActive = getItemState("pOther_Automatic_State_Solar") == ON
                    #if itemLastUpdateOlderThen("pGF_Garage_Solar_Inverter_Total_Yield", ZonedDateTime.now().minusHours(5) if solarActive else ZonedDateTime.now().minusHours(14)):
                    if (itemLastUpdateOlderThen("pGF_Garage_Solar_Inverter_Total_Yield", ZonedDateTime.now().minusMinutes(15)) 
                       or (itemLastUpdateOlderThen("pGF_Garage_Solar_Inverter_AC_Power", ZonedDateTime.now().minusMinutes(60)) and getItemState("pGF_Garage_Solar_Inverter_AC_Power").intValue() > 0)):
                        #  and 
                        #(itemLastUpdateOlderThen("pGF_Garage_Solar_Inverter_AC_Power", ZonedDateTime.now().minusMinutes(15)) or getItemState("pGF_Garage_Solar_Inverter_AC_Power").intValue() == 0)):
                        if postUpdateIfChanged("pGF_Garage_Solar_Inverter_Is_Working",OFF):
                            postUpdate("pGF_Garage_Solar_Inverter_AC_Power",0)
                            postUpdateIfChanged("pGF_Garage_Solar_Inverter_DC_Power",0)
                            postUpdateIfChanged("pGF_Garage_Solar_Inverter_DC_Current",0)
                            postUpdateIfChanged("pGF_Garage_Solar_Inverter_DC_Voltage",0)
                            postUpdateIfChanged("pGF_Garage_Solar_Inverter_Daily_Yield",0)
                    else:
                        postUpdateIfChanged("pGF_Garage_Solar_Inverter_Is_Working",ON)

                # triggers solar value update
                sendCommand("pGF_Garage_Solar_Inverter_AC_Power",REFRESH)
            else:
                self.updateConsumption(0)
                postUpdateIfChanged("pGF_Garage_Solar_Inverter_Is_Working",ON)
            postUpdateIfChanged("pGF_Utilityroom_Electricity_Current_Demand",self.currentDemand)


@rule("values_consumption.py")
class EnergyDailyConsumptionRule:
    def __init__(self):
        self.triggers = [
          #ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Current_Daily_Demand"),
          #ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Current_Daily_Supply"),
          #ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_Daily_Yield")
          # should be cron based, otherwise it will create until 3 times more values if it is based on ItemStateChangeTrigger
          CronTrigger("30 */5 * * * ?")
        ]

    def execute(self, module, input):
        dailyEnergyDemand = getItemState("pGF_Utilityroom_Electricity_Current_Daily_Demand").doubleValue()
        dailyEnergySupply = getItemState("pGF_Utilityroom_Electricity_Current_Daily_Supply").doubleValue()
        dailySolarSupply = getItemState("pGF_Garage_Solar_Inverter_Daily_Yield").doubleValue()

        postUpdateIfChanged("pGF_Utilityroom_Electricity_Current_Daily_Consumption",dailyEnergyDemand - dailyEnergySupply + dailySolarSupply)

@rule("values_consumption.py")
class SolarConsumptionRule:
    def __init__(self):
        self.triggers = [
          #ItemStateChangeTrigger("Electricity_Meter_Supply"),
          #ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_Total_Yield"),
          # should be cron based, otherwise it will create until 3 times more values if it is based on ItemStateChangeTrigger
          CronTrigger("15 */5 * * * ?")
        ]

    def execute(self, module, input):
        now = ZonedDateTime.now()
      
        currentSupply = getItemState("pGF_Utilityroom_Electricity_Total_Supply").doubleValue()
        currentYield = getItemState("pGF_Garage_Solar_Inverter_Total_Yield").doubleValue()
        
        # Tagesverbrauch
        startSupply = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Supply", now.toLocalDate().atStartOfDay(now.getZone()) ).doubleValue()
        startYield = getHistoricItemState("pGF_Garage_Solar_Inverter_Total_Yield", now.toLocalDate().atStartOfDay(now.getZone()) ).doubleValue()

        # sometimes solar converter is providing wrong value. Mostly if he is inactive in the night
        if currentYield > 1000000000 or startYield > 1000000000:
            # can be INFO because it is a 'normal' behavior of this  solar converter
            self.log.info(u"Wrong Solar Value: currentYield is {}, startYield is {}".format(currentYield,startYield))
            return

        totalSupply = currentSupply - startSupply
        totalYield = currentYield - startYield
        dailyConsumption = totalYield - totalSupply
        
        postUpdateIfChanged("pGF_Garage_Solar_Inverter_Daily_Yield",totalYield)
        
        #self.log.info(u"A {} {}".format(currentSupply,currentYield))
        #self.log.info(u"B {} {}".format(startSupply,startYield))
        #self.log.info(u"C {} {}".format(totalSupply,totalYield))
        
        postUpdateIfChanged("pGF_Garage_Solar_Inverter_Daily_Consumption",dailyConsumption)
        
        # Jahresverbrauch
        refDay = now.withYear(now.getYear()).withMonth(1).withDayOfMonth(1)
        refDate = refDay.toLocalDate().atStartOfDay(refDay.getZone())
        startSupply = getHistoricItemState("pGF_Utilityroom_Electricity_Total_Supply", refDate ).doubleValue()
        startYield = getHistoricItemState("pGF_Garage_Solar_Inverter_Total_Yield", refDate ).doubleValue()

        totalSupply = currentSupply - startSupply
        totalYield = currentYield - startYield
        annualConsumption = totalYield - totalSupply
        
        #self.log.info(u"D {} {}".format(startSupply,startYield))
        #self.log.info(u"E {}".format(annualConsumption))
        
        postUpdateIfChanged("pGF_Garage_Solar_Inverter_Annual_Consumption",annualConsumption)


@rule("values_consumption.py")
class GasConsumptionDailyRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 0 * * ?")]

    def execute(self, module, input):
        postUpdateIfChanged("pGF_Utilityroom_Gas_Current_Daily_Consumption",0)

@rule("values_consumption.py")
class GasConsumption5MinRule:
    def __init__(self):
        self.triggers = [CronTrigger("15 */5 * * * ?")]

    def execute(self, module, input):
        value5Min = getHistoricReference( self.log, "pGF_Utilityroom_Gas_Meter_Current_Count", 300, 615, 900, 300 )
        postUpdateIfChanged("pGF_Utilityroom_Gas_Current_Consumption",value5Min)

@rule("values_consumption.py")
class GasConsumptionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pGF_Utilityroom_Gas_Meter_Pulse_Counter")]

    def execute(self, module, input):
        now = ZonedDateTime.now()
        Aktuell_End = getItemState("pGF_Utilityroom_Gas_Meter_Pulse_Counter").doubleValue()

        # Aktueller Zählerstand
        zaehlerStandCurrent = startGasMeterValue + ((Aktuell_End - startGasImpulseCounter) * 0.01)

        zaehlerStandSaved = getItemStateWithFallback("pGF_Utilityroom_Gas_Meter_Current_Count",DecimalType(0.0)).doubleValue()
        
        #self.log.info("{}".format(zaehlerStandCurrent))
        
        if zaehlerStandCurrent < zaehlerStandSaved:
            self.log.error("Consumption: Calculation is wrong {} {}".format(zaehlerStandCurrent,zaehlerStandSaved))
            return

        if zaehlerStandCurrent > zaehlerStandSaved:
            # Aktueller Zählerstand
            postUpdate("pGF_Utilityroom_Gas_Meter_Current_Count", zaehlerStandCurrent )

        # *** Aktueller Tagesverbrauch ***
        zaehlerStandOld = getHistoricItemState("pGF_Utilityroom_Gas_Meter_Current_Count", now.toLocalDate().atStartOfDay(now.getZone()) ).doubleValue()
        currentConsumption = zaehlerStandCurrent - zaehlerStandOld
        if currentConsumption < 0:
            currentConsumption = 0

        postUpdateIfChanged("pGF_Utilityroom_Gas_Current_Daily_Consumption",currentConsumption)

        # *** Jahresverbrauch ***
        refDay = now.withYear(now.getYear()).withMonth(1).withDayOfMonth(1)
        zaehlerStandOld = getHistoricItemState("pGF_Utilityroom_Gas_Meter_Current_Count", refDay.toLocalDate().atStartOfDay(refDay.getZone())).doubleValue()
        currentConsumption = zaehlerStandCurrent - zaehlerStandOld
        if currentConsumption < 0:
            currentConsumption = 0

        if postUpdateIfChanged("pGF_Utilityroom_Gas_Annual_Consumption", currentConsumption ):
            # Hochrechnung
            zaehlerStandCurrentOneYearBefore = getHistoricItemState("pGF_Utilityroom_Gas_Meter_Current_Count", now.minusYears(1) ).doubleValue()
            forecastConsumtion = zaehlerStandOld - zaehlerStandCurrentOneYearBefore

            refDay = now.withYear(now.getYear()-1).withMonth(1).withDayOfMonth(1)
            zaehlerStandOldOneYearBefore = getHistoricItemState("pGF_Utilityroom_Gas_Meter_Current_Count", refDay.toLocalDate().atStartOfDay(refDay.getZone())).doubleValue()

            hochrechnungVerbrauch = round( currentConsumption + forecastConsumtion )

            msg = u"{} m³, {} m³".format(hochrechnungVerbrauch,int( round( zaehlerStandOld - zaehlerStandOldOneYearBefore ) ))
            postUpdate("pGF_Utilityroom_Gas_Forecast", msg )
