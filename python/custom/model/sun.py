# -*- coding: utf-8 -*-

import time
import math
from org.joda.time import DateTimeZone

from custom.helper import getItemState

class SunRadiation(object): 
    @staticmethod
    def _getSunData( time ):
        # Constants                                                                                                                                                                                                                                 
        K = 0.017453                                                                                                                                                                                                                      

        # Change this reflecting your destination                                                                                                                                                                                                   
        latitude = 52.347767                                                                                                                                                                                                              
        longitude = 13.621287

        # allways +1 Berlin winter time
        local = time.toDateTime(DateTimeZone.forOffsetHours(1))

        day = local.getDayOfYear()
        hour = local.getHourOfDay() + (local.getMinuteOfHour()/60.0)

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
    def getSunPowerPerHour( referenceTime, cloudCover, currentRadiation = None ):

        elevation, azimut = SunRadiation._getSunData( referenceTime )

        # 125° 1/2 der Hauswand	
        southMultiplier = 0
        if azimut >= 120 and azimut <= 260 and ( currentRadiation != None or elevation >= 10.0 ):
            # 100° (0) => -1 (0)
            # 260° (160) => 1 (2)
            southX = ( ( azimut - 100.0 ) * 2.0 / 160.0 ) - 1.0
            southMultiplier = ( math.pow( southX, 10.0 ) * -1.0 ) + 1.0

        westMultiplier = 0
        minElevation = 0
        if azimut >= 220 and azimut <= 285:
            #10 -> 20
            minElevation = ( ( azimut - 220 ) * 10.0 / 65.0 ) + 10.0
            if currentRadiation != None or elevation >= minElevation:
                # https://rechneronline.de/funktionsgraphen/
                # 190° (0) => -1 (0)
                # 350° (160) => 1 (2)           
                westX = ( ( azimut - 190.0 ) * 2.0 / 160.0 ) - 1.0
                westMultiplier = ( math.pow( westX, 10.0 ) * -1.0 ) + 1.0

        southActive = southMultiplier > 0.0
        westActive  = westMultiplier > 0.0
        
        # in the morning the sun must be above 20°
        # and in the evening the sun must be above 10°
        if southActive or westActive:
            if currentRadiation is None:
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
                _currentRadiation = _maxRadiation * ( 1.0 - 0.75 * math.pow( _cloudCoverFactor, 3.4 ) )
            else:
                _currentRadiation = currentRadiation

            _effectiveSouthRadiation = _currentRadiation * southMultiplier
            _effectiveWestRadiation = _currentRadiation * westMultiplier
            
            activeDirections = []
            if southActive: activeDirections.append("S")
            if westActive: activeDirections.append("W")
            activeMsg = u" • {}".format("+".join(activeDirections))
        else:
            _activeRadiation = 0.0
            _effectiveSouthRadiation = 0.0
            _effectiveWestRadiation = 0.0

            activeMsg = u""
            
        sunElevationMsg = int( round( elevation, 0 ) )
        sunAzimutMsg = int( round( azimut, 0 ) )
      
        minElevationMsg = u" ({})".format( int( round( minElevation)) ) if minElevation > 0 else ""
        debugInfo = u"Azimut {}° • Elevation {}°{}• Clouds {} octas{}".format(sunAzimutMsg, sunElevationMsg, minElevationMsg, cloudCover, activeMsg)

        return _effectiveSouthRadiation, _effectiveWestRadiation, debugInfo

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
