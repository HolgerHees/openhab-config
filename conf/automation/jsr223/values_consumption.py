from org.joda.time import DateTime
from org.joda.time.format import DateTimeFormat

from custom.helper import rule, getNow, getHistoricItemEntry, getHistoricItemState, getItemLastChange, itemLastUpdateOlderThen, itemLastChangeOlderThen, getItemState, postUpdate, postUpdateIfChanged, sendCommand
from core.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger

from org.eclipse.smarthome.core.types.RefreshType import REFRESH

totalSupply = 3600 # total possible photovoltaic power in watt
maxTimeSlot = 300000 # value timeslot to messure average power consumption => 5 min

energyTotalDemandCorrectureFactor = 1.045
energyTotalSupplyCorrectureFactor = 1.00

# offset values for total energy demand and supply (total values at the time when knx based energy meter was installed)
startEnergyTotalDemandValue = 21158.037
startEnergyTotalSupplyValue = -90.636

# offset values for electricity meter demand and supply (total values at the time when new electricity meter was changed)
startElectricityMeterDemandValue = 21911.164
startElectricityMeterSupplyValue = 0

# offset values for gas meter (total value at the time when knx based impulse counter was resettet)
startGasMeterValue = 8573.39
startGasImpulseCounter = 0

dateTimeFormatter = DateTimeFormat.forPattern("yyyy-MM-dd HH:mm:ss.SSS")

def getHistoricReference(log, itemName, valueTime, outdatetTime, messureTime, intervalTime):
    endTime = getItemLastChange(itemName)
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

    startTime = DateTime(startTimestampInMillis)
    log.info( u"Consumption {} messured from {} ({}) to {} ({})".format(value,startValue,dateTimeFormatter.print(startTime),endValue,dateTimeFormatter.print(endTime)))

    return value

@rule("values_consumption.py")
class SolarPower5minRule:
    def __init__(self):
        self.triggers = [CronTrigger("45 */30 * * * ?")]

    def execute(self, module, input):
        value5Min = getHistoricReference(self.log, "Heating_Solar_Power", 300, 3600, 5600, 1800)
        postUpdateIfChanged("Heating_Solar_Power_Current5Min",value5Min)


@rule("values_consumption.py")
class EnergyCounterDemandRule:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("Energy_Demand_Active"),
          CronTrigger("1 0 0 * * ?")
        ]

    def execute(self, module, input):
        now = getNow()
        
        demandCurrent = getItemState("Energy_Demand_Active").intValue() / 1000.0
        zaehlerStandCurrent = ( startEnergyTotalDemandValue + demandCurrent )
        postUpdateIfChanged("Electricity_Total_Demand",zaehlerStandCurrent)
        
        postUpdateIfChanged("Electricity_Meter_Demand",(zaehlerStandCurrent-startElectricityMeterDemandValue) * energyTotalDemandCorrectureFactor)

        # *** Tagesbezug ***
        zaehlerStandOld = getHistoricItemState("Electricity_Total_Demand", now.withTimeAtStartOfDay() ).doubleValue()
        currentDemand = zaehlerStandCurrent - zaehlerStandOld
        
        postUpdateIfChanged("Electricity_Current_Daily_Demand",currentDemand)

        # *** Jahresbezug ***
        zaehlerStandOld = getHistoricItemState("Electricity_Total_Demand", now.withDate(now.getYear(), 1, 1 ).withTimeAtStartOfDay()).doubleValue()
        currentDemand = zaehlerStandCurrent - zaehlerStandOld

        if postUpdateIfChanged("Electricity_Current_Annual_Demand", currentDemand ):
            # Hochrechnung
            zaehlerStandCurrentOneYearBefore = getHistoricItemState("Electricity_Total_Demand", now.minusYears(1) ).doubleValue()
            forecastDemand = zaehlerStandOld - zaehlerStandCurrentOneYearBefore

            zaehlerStandOldOneYearBefore = getHistoricItemState("Electricity_Total_Demand", now.withDate(now.getYear()-1, 1, 1 ).withTimeAtStartOfDay()).doubleValue()

            hochrechnungDemand = int( round( currentDemand + forecastDemand ) )
            vorjahresDemand = int( round( zaehlerStandOld - zaehlerStandOldOneYearBefore ) )
            msg = u"{} kWh, {} kWh".format(hochrechnungDemand,vorjahresDemand)
            postUpdate("Electricity_Current_Annual_Demand_Forecast", msg )


@rule("values_consumption.py")
class EnergyCounterSupplyRule:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("Energy_Supply_Active"),
          CronTrigger("1 0 0 * * ?")
        ]

    def execute(self, module, input):
        now = getNow()
        
        supplyCurrent = getItemState("Energy_Supply_Active").intValue() / 1000.0
        zaehlerStandCurrent = ( startEnergyTotalSupplyValue + supplyCurrent )
        postUpdateIfChanged("Electricity_Total_Supply",zaehlerStandCurrent)

        postUpdateIfChanged("Electricity_Meter_Supply",(zaehlerStandCurrent-startElectricityMeterSupplyValue) * energyTotalSupplyCorrectureFactor)

        # *** Tageslieferung ***
        zaehlerStandOld = getHistoricItemState("Electricity_Total_Supply", now.withTimeAtStartOfDay() ).doubleValue()
        currentSupply = zaehlerStandCurrent - zaehlerStandOld

        postUpdateIfChanged("Electricity_Current_Daily_Supply",currentSupply)
        # *** Jahreslieferung ***

        zaehlerStandOld = getHistoricItemState("Electricity_Total_Supply", now.withDate(now.getYear(), 1, 1 ).withTimeAtStartOfDay()).doubleValue()
        currentSupply = zaehlerStandCurrent - zaehlerStandOld

        if postUpdateIfChanged("Electricity_Current_Annual_Supply", currentSupply ):
            # Hochrechnung
            zaehlerStandCurrentOneYearBefore = getHistoricItemState("Electricity_Total_Supply", now.minusYears(1) ).doubleValue()
            forecastSupply = zaehlerStandOld - zaehlerStandCurrentOneYearBefore

            zaehlerStandOldOneYearBefore = getHistoricItemState("Electricity_Total_Supply", now.withDate(now.getYear()-1, 1, 1 ).withTimeAtStartOfDay()).doubleValue()

            hochrechnungSupply = int( round( currentSupply + forecastSupply ) )
            vorjahresSupply = int( round( zaehlerStandOld - zaehlerStandOldOneYearBefore ) )
            msg = u"{}kWh, {} kWh".format(hochrechnungSupply,vorjahresSupply)
            postUpdate("Electricity_Current_Annual_Supply_Forecast", msg )


@rule("values_consumption.py")
class EnergySupplyRule:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("Electricity_Current_Consumption"),
          CronTrigger("0 */5 * * * ?")
        ]

        self.stack = []
        self.lastLimitationIncrease = 0
        
    def getAvgConsumption(self,now,value):        
        if len(self.stack) > 0:
            avgValue = 0
            currentTime = now
            currentTimeSlot = 0
                  
            for index, x in enumerate( reversed(self.stack) ):           
                #self.log.info(u"{}".format(DateTime(currentTime)))
                
                # remove values older then 5 minutes
                if currentTimeSlot >= maxTimeSlot and len(self.stack) > index:
                    #self.log.info(u"remove samples after index {}".format(len(self.stack)-index))
                    self.stack = self.stack[len(self.stack)-index:]
                    break;

                avgValue += x[0] * ( currentTime - x[1] )
                currentTime = x[1]
                currentTimeSlot = now - currentTime
                  
            avgValue = avgValue / ( now - currentTime )
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
      
        now = getNow().getMillis()
        
        currentACPower = getItemState("Solar_AC_Power").intValue()

        currentPowerLimitation = getItemState("Solar_Power_Limitation").intValue()

        currentConsumptionValue = getItemState("Electricity_Current_Consumption").intValue()
        # must be called to fill history stack
        avgConsumptionValue = self.getAvgConsumption(now,currentConsumptionValue)
        
        if currentACPower > 0:
            possiblePowerLimitation = self.getPossibleLimitation(currentConsumptionValue)
            possibleAvgPowerLimitation = self.getPossibleLimitation(avgConsumptionValue)
            
            self.log.info(u"currentLimit: {}%, currentConsumption: {}W, avgConsumption: {}W, possibleLimit: {}%, possibleAvgLimit: {}%, stack: {}, li: {}".format(currentPowerLimitation,currentConsumptionValue,avgConsumptionValue,possiblePowerLimitation,possibleAvgPowerLimitation,len(self.stack),(now - self.lastLimitationIncrease)))

            if possiblePowerLimitation >= currentPowerLimitation:
                self.lastLimitationIncrease = now
                if possiblePowerLimitation > currentPowerLimitation:
                    sendCommand("Solar_Power_Limitation",possiblePowerLimitation)
                    self.log.info(u"Increase power limitation from {}% to {}%".format( currentPowerLimitation, possiblePowerLimitation ))
                    return
            elif now - self.lastLimitationIncrease > maxTimeSlot:
                if possibleAvgPowerLimitation < currentPowerLimitation:
                    sendCommand("Solar_Power_Limitation",possibleAvgPowerLimitation)
                    self.log.info(u"Decrease power limitation from {}% to {}%".format( currentPowerLimitation, possibleAvgPowerLimitation ))
                    return
                
            if len(input) == 0 and itemLastChangeOlderThen("Solar_Power_Limitation",getNow().minusMinutes(4)):
                sendCommand("Solar_Power_Limitation",currentPowerLimitation)
                self.log.info(u"Refresh power limitation of {}%".format( currentPowerLimitation ))
        elif currentPowerLimitation != 100:
            postUpdate("Solar_Power_Limitation",100)
            self.log.info(u"Shutdown power limitation")

@rule("values_consumption.py")
class EnergyTotalYieldRefreshRule:
    def __init__(self):
        self.triggers = [
          CronTrigger("0 * * * * ?")
        ]
        
    def execute(self, module, input):
        if getItemState("State_Solar") == ON:
            # triggers solar value update
            sendCommand("Solar_Total_Yield",REFRESH)
        
@rule("values_consumption.py")
class EnergyCurrentDemandAndConsumptionRule:
    def __init__(self):
        self.triggers = [
          ItemStateChangeTrigger("Power_Demand_Active"),
          ItemStateChangeTrigger("Power_Supply_Active"),
          ItemStateUpdateTrigger("Solar_AC_Power")
        ]
        
    def updateConsumption(self,solarPower):
        consumption = self.currentDemand + solarPower
        
        if consumption > 0:
            postUpdateIfChanged("Electricity_Current_Consumption",consumption)
        else:
            self.log.info(u"Skip consumption update. powerDemand: {}, powerSupply: {}, solarPower: {}".format(self.powerDemand,self.powerSupply,solarPower))

    def execute(self, module, input):
        if input["event"].getItemName() == "Solar_AC_Power":
            self.updateConsumption(input['event'].getItemState().intValue())
        else:
            if input["event"].getItemName() == "Power_Demand_Active":
                self.powerDemand = input["event"].getItemState().intValue()
                self.powerSupply = getItemState("Power_Supply_Active").intValue()
                
                if self.powerDemand != getItemState("Power_Demand_Active").intValue():
                    self.log.error("Item demand state differences: {}, item state: {}".format(self.powerDemand,getItemState("Power_Demand_Active").intValue()))
            else:
                self.powerDemand = getItemState("Power_Demand_Active").intValue()
                self.powerSupply = input["event"].getItemState().intValue()
                
                if self.powerSupply != getItemState("Power_Supply_Active").intValue():
                    self.log.error("Item supply state differences: {}, item state: {}".format(self.powerSupply,getItemState("Power_Supply_Active").intValue()))

            self.currentDemand = self.powerDemand - self.powerSupply
            
            if getItemState("State_Solar") == ON:
                # solar value update was not successful for a while
                #solarActive = getItemState("State_Solar") == ON
                #if itemLastUpdateOlderThen("Solar_Total_Yield", getNow().minusHours(5) if solarActive else getNow().minusHours(14)):
                if itemLastUpdateOlderThen("Solar_Total_Yield", getNow().minusHours(24)):
                    self.log.info(u"Solar: ERROR • Values not updated. Fallback to '0' values.")
                    postUpdate("Solar_AC_Power",0)
                    postUpdateIfChanged("Solar_DC_Power",0)
                    postUpdateIfChanged("Solar_DC_Current",0)
                    postUpdateIfChanged("Solar_DC_Voltage",0)
                    postUpdateIfChanged("Solar_Daily_Yield",0)

                # triggers solar value update
                sendCommand("Solar_AC_Power",REFRESH)
            else:
                self.updateConsumption(0)

            postUpdateIfChanged("Electricity_Current_Demand",self.currentDemand)


@rule("values_consumption.py")
class EnergyDailyConsumptionRule:
    def __init__(self):
        self.triggers = [
          #ItemStateChangeTrigger("Electricity_Current_Daily_Demand"),
          #ItemStateChangeTrigger("Electricity_Current_Daily_Supply"),
          #ItemStateChangeTrigger("Solar_Daily_Yield")
          # should be cron based, otherwise it will create until 3 times more values if it is based on ItemStateChangeTrigger
          CronTrigger("30 */5 * * * ?")
        ]

    def execute(self, module, input):
        dailyEnergyDemand = getItemState("Electricity_Current_Daily_Demand").doubleValue()
        dailyEnergySupply = getItemState("Electricity_Current_Daily_Supply").doubleValue()
        dailySolarSupply = getItemState("Solar_Daily_Yield").doubleValue()

        postUpdateIfChanged("Electricity_Current_Daily_Consumption",dailyEnergyDemand - dailyEnergySupply + dailySolarSupply)

@rule("values_consumption.py")
class SolarConsumptionRule:
    def __init__(self):
        self.triggers = [
          #ItemStateChangeTrigger("Electricity_Meter_Supply"),
          #ItemStateChangeTrigger("Solar_Total_Yield"),
          # should be cron based, otherwise it will create until 3 times more values if it is based on ItemStateChangeTrigger
          CronTrigger("15 */5 * * * ?")
        ]

    def execute(self, module, input):
        now = getNow()
      
        currentSupply = getItemState("Electricity_Total_Supply").doubleValue()
        currentYield = getItemState("Solar_Total_Yield").doubleValue()
        
        # Tagesverbrauch
        startSupply = getHistoricItemState("Electricity_Total_Supply", now.withTimeAtStartOfDay() ).doubleValue()
        startYield = getHistoricItemState("Solar_Total_Yield", now.withTimeAtStartOfDay() ).doubleValue()

        # sometimes solar converter is providing wrong value. Mostly if he is inactive in the night
        if currentYield > 1000000000 or startYield > 1000000000:
            # can be INFO because it is a 'normal' behavior of this  solar converter
            self.log.info(u"Wrong Solar Value: currentYield is {}, startYield is {}".format(currentYield,startYield))
            return

        totalSupply = currentSupply - startSupply
        totalYield = currentYield - startYield
        dailyConsumption = totalYield - totalSupply
        
        postUpdateIfChanged("Solar_Daily_Yield",totalYield)
        
        #self.log.info(u"A {} {}".format(currentSupply,currentYield))
        #self.log.info(u"B {} {}".format(startSupply,startYield))
        #self.log.info(u"C {} {}".format(totalSupply,totalYield))
        
        postUpdateIfChanged("Solar_Daily_Consumption",dailyConsumption)
        
        # Jahresverbrauch
        startSupply = getHistoricItemState("Electricity_Total_Supply", now.withDate(now.getYear(), 1, 1 ).withTimeAtStartOfDay() ).doubleValue()
        startYield = getHistoricItemState("Solar_Total_Yield", now.withDate(now.getYear(), 1, 1 ).withTimeAtStartOfDay() ).doubleValue()

        totalSupply = currentSupply - startSupply
        totalYield = currentYield - startYield
        annualConsumption = totalYield - totalSupply
        
        #self.log.info(u"D {} {}".format(startSupply,startYield))
        #self.log.info(u"E {}".format(annualConsumption))
        
        postUpdateIfChanged("Solar_Annual_Consumption",annualConsumption)


@rule("values_consumption.py")
class GasConsumptionRule:
    def __init__(self):
        self.triggers = [CronTrigger("15 */5 * * * ?")]

    def execute(self, module, input):
        now = getNow()
        Aktuell_End = getItemState("Gas_Pulse_Counter").doubleValue()

        # Aktueller Zählerstand
        zaehlerStandCurrent = startGasMeterValue + ((Aktuell_End - startGasImpulseCounter) * 0.01)

        zaehlerStandSaved = getItemState("Gas_Current_Count").doubleValue()
        
        #self.log.info("{}".format(zaehlerStandCurrent))
        
        if zaehlerStandCurrent < zaehlerStandSaved:
            self.log.error("Consumption: Calculation is wrong {} {}".format(zaehlerStandCurrent,zaehlerStandSaved))
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
        zaehlerStandOld = getHistoricItemState("Gas_Current_Count", now.withDate(now.getYear(), 1, 1 ).withTimeAtStartOfDay()).doubleValue()
        currentConsumption = zaehlerStandCurrent - zaehlerStandOld
        if currentConsumption < 0:
            currentConsumption = 0

        if postUpdateIfChanged("Gas_Annual_Consumption", currentConsumption ):
            # Hochrechnung
            zaehlerStandCurrentOneYearBefore = getHistoricItemState("Gas_Current_Count", now.minusYears(1) ).doubleValue()
            forecastConsumtion = zaehlerStandOld - zaehlerStandCurrentOneYearBefore

            zaehlerStandOldOneYearBefore = getHistoricItemState("Gas_Current_Count", now.withDate(now.getYear()-1, 1, 1 ).withTimeAtStartOfDay()).doubleValue()

            hochrechnungVerbrauch = round( currentConsumption + forecastConsumtion )

            msg = u"{} m³, {} m³".format(hochrechnungVerbrauch,int( round( zaehlerStandOld - zaehlerStandOldOneYearBefore ) ))
            postUpdate("Gas_Forecast", msg )
