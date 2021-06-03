# -*- coding: utf-8 -*-
import time
import math
from java.time import ZoneOffset
    
class SunRadiation(object):
    # haus um 3.2 grad gedreht
    # 3.2492105921044496
    AZIMUT_GARDEN_DEVIATION  = 3.3
    AZIMUT_NW_LIMIT = 290.0

    @staticmethod
    def _getSunData( time ):
        # Constants                                                                                                                                                                                                                                 
        K = 0.017453                                                                                                                                                                                                                      

        # Change this reflecting your destination                                                                                                                                                                                                   
        latitude = 52.347767                                                                                                                                                                                                              
        longitude = 13.621287

        # allways +1 Berlin winter time
        local = time.withZoneSameInstant(ZoneOffset.ofHours(1))

        day = local.getDayOfYear()
        hour = local.getHour() + (local.getMinute()/60.0)

        # Source: http://www.jgiesen.de/SME/tk/index.htm
        deklination = -23.45 * math.cos( K * 360 * (day + 10) / 365 )
        zeitgleichung = 60.0 * (-0.171 * math.sin( 0.0337*day+0.465) - 0.1299 * math.sin( 0.01787*day-0.168))
        stundenwinkel = 15.0 * ( hour - (15.0-longitude)/15.0 - 12.0 + zeitgleichung/60.0)
        x = math.sin(K * latitude) * math.sin(K * deklination) + math.cos(K * latitude) * math.cos(K * deklination) * math.cos(K * stundenwinkel)
        y = - (math.sin(K*latitude) * x - math.sin(K*deklination)) / (math.cos(K*latitude) * math.sin(math.acos(x)))
        elevation = math.asin(x) / K

        isBreak = hour <= 12.0 + (15.0-longitude)/15.0 - zeitgleichung/60.0
        if isBreak: azimut = math.acos(y) / K
        else: azimut = 360.0 - math.acos(y) / K

        return elevation, azimut

    @staticmethod
    def getMinElevation( azimut ):
        minElevation = 9.0
        #10 -> 20
        if azimut >= 220.0:
            if azimut <= SunRadiation.AZIMUT_NW_LIMIT:
                minElevation = ( ( azimut - 220.0 ) * 5.0 / ( SunRadiation.AZIMUT_NW_LIMIT - 220.0 ) ) + 9.0
            elif azimut <= 365:
                minElevation = 14.0
        return minElevation

    @staticmethod
    def getSunPowerPerHour( referenceTime, cloudCover, sunRadiation = None, sunRadiationLazy = None ):

        elevation, azimut = SunRadiation._getSunData( referenceTime )

        minElevation = SunRadiation.getMinElevation(azimut)
        
        southMultiplier = 0
        westMultiplier = 0
        
        if sunRadiation != None or elevation >= minElevation:
            # https://rechneronline.de/funktionsgraphen/
            # x^2 * -1 + 1
            # x^4 * -1 + 1
            
            
            _start = 110.0 + SunRadiation.AZIMUT_GARDEN_DEVIATION
            _end = 250.0 + SunRadiation.AZIMUT_GARDEN_DEVIATION
            if azimut >= _start and azimut <= _end:
                # 110° (0) => -1 (0)
                # 250° (140) => 1 (2)
                southX = ( ( azimut - _start ) * 2.0 / ( _end - _start ) ) - 1.0
                southMultiplier = ( math.pow( southX, 10.0 ) * -1.0 ) + 1.0

            _start = 200.0 + SunRadiation.AZIMUT_GARDEN_DEVIATION
            _end = 340.0 + SunRadiation.AZIMUT_GARDEN_DEVIATION
            if azimut >= _start and azimut <= SunRadiation.AZIMUT_NW_LIMIT:
                # 200° (0) => -1 (0)
                # 340° (140) => 1 (2)           
                westX = ( ( azimut - _start ) * 2.0 / ( _end - _start ) ) - 1.0
                westMultiplier = ( math.pow( westX, 10.0 ) * -1.0 ) + 1.0

        if sunRadiation is None:
            _usedRadians = math.radians(elevation)
            if _usedRadians < 0.0: _usedRadians = 0.0
            
            # Cloud Cover is between 0 and 9 - but converting to 0 and 8
            # https://en.wikipedia.org/wiki/Okta
            _cloudCover = cloudCover
            if _cloudCover > 8.0: _cloudCover = 8.0
            _cloudCoverFactor = _cloudCover / 8.0
            
            # http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/
            # http://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf
            _maxRadiation = 990.0 * math.sin( _usedRadians ) - 30.0
            if _maxRadiation < 0.0: _maxRadiation = 0.0
            _effectiveRadiation = _maxRadiation * ( 1.0 - 0.75 * math.pow( _cloudCoverFactor, 3.4 ) )
        else:
            _effectiveRadiation = sunRadiation

        _effectiveSouthRadiation = _effectiveRadiation * southMultiplier
        _effectiveWestRadiation = _effectiveRadiation * westMultiplier
        
        activeDirections = []
        if southMultiplier > 0.0: activeDirections.append("S")
        if westMultiplier > 0.0: activeDirections.append("W")
        activeMsg = u" • {}".format("+".join(activeDirections)) if len(activeDirections) > 0 else u""
        
        sunElevationMsg = int( round( elevation, 0 ) )
        sunAzimutMsg = int( round( azimut, 0 ) )
      
        minElevationMsg = u" (min {})".format( int( round( minElevation)) ) if minElevation > 0 else ""
        lazyRadiationMsg = u" (∾ {})".format( round(sunRadiationLazy / 60.0, 1) ) if sunRadiationLazy != None else ""
        debugInfo = u"Azimut {}° • Elevation {}{}° • Clouds {} octas • Sun {}{} W/min{}".format(sunAzimutMsg, sunElevationMsg, minElevationMsg, cloudCover, round(_effectiveRadiation / 60.0, 1), lazyRadiationMsg, activeMsg)

        return _effectiveSouthRadiation, _effectiveWestRadiation, _effectiveRadiation, debugInfo

    @staticmethod
    def getWindowSunPowerPerHour( area, radiation ):
        # https://de.wikipedia.org/wiki/Energiedurchlassgrad
        # https://www.fensterversand.com/info/qualitaet/g-wert-fenster.php
        # https://www.fensterversand.com/fenster/verglasung/dreifachverglasung.php
        # G Value of 0.55 "3-Windowpane heat reflecting glass"
        return area * radiation * 0.55

    @staticmethod
    def getWallSunPowerPerHour( area, radiation ):
        # 66.2 is the lazyness of the wall
        return area * radiation / 66.2
