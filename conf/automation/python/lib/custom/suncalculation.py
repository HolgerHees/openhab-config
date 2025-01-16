import time
import math

class SunRadiation():
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

        day = time.timetuple().tm_yday
        hour = time.hour + (time.minute / 60.0)

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
        min_elevation = 9.0
        #10 -> 20
        if azimut >= 220.0:
            if azimut <= SunRadiation.AZIMUT_NW_LIMIT:
                min_elevation = ( ( azimut - 220.0 ) * 5.0 / ( SunRadiation.AZIMUT_NW_LIMIT - 220.0 ) ) + 9.0
            elif azimut <= 365:
                min_elevation = 14.0
        return min_elevation

    @staticmethod
    def getSunPowerPerHour( reference_time, cloud_cover, sun_radiation = None ):

        elevation, azimut = SunRadiation._getSunData( reference_time )

        min_elevation = SunRadiation.getMinElevation(azimut)
        
        south_multiplier = 0
        west_multiplier = 0
        
        if sun_radiation != None or elevation >= min_elevation:
            # https://rechneronline.de/funktionsgraphen/
            # x^2 * -1 + 1
            # x^4 * -1 + 1
            
            
            _start = 110.0 + SunRadiation.AZIMUT_GARDEN_DEVIATION
            _end = 250.0 + SunRadiation.AZIMUT_GARDEN_DEVIATION
            if azimut >= _start and azimut <= _end:
                # 110° (0) => -1 (0)
                # 250° (140) => 1 (2)
                southX = ( ( azimut - _start ) * 2.0 / ( _end - _start ) ) - 1.0
                south_multiplier = ( math.pow( southX, 10.0 ) * -1.0 ) + 1.0

            _start = 200.0 + SunRadiation.AZIMUT_GARDEN_DEVIATION
            _end = 340.0 + SunRadiation.AZIMUT_GARDEN_DEVIATION
            if azimut >= _start and azimut <= SunRadiation.AZIMUT_NW_LIMIT:
                # 200° (0) => -1 (0)
                # 340° (140) => 1 (2)           
                west_x = ( ( azimut - _start ) * 2.0 / ( _end - _start ) ) - 1.0
                west_multiplier = ( math.pow( west_x, 10.0 ) * -1.0 ) + 1.0

        if sun_radiation is None:
            _used_radians = math.radians(elevation)
            if _used_radians < 0.0: _used_radians = 0.0
            
            # Cloud Cover is between 0 and 9 - but converting to 0 and 8
            # https://en.wikipedia.org/wiki/Okta
            _cloud_cover = cloud_cover
            if _cloud_cover > 8.0: _cloud_cover = 8.0
            _cloud_coverFactor = _cloud_cover / 8.0
            
            # http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/
            # http://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf
            _max_radiation = 990.0 * math.sin( _used_radians ) - 30.0
            if _max_radiation < 0.0: _max_radiation = 0.0
            _effective_radiation = _max_radiation * ( 1.0 - 0.75 * math.pow( _cloud_coverFactor, 3.4 ) )
        else:
            _effective_radiation = sun_radiation

        _effective_south_radiation = _effective_radiation * south_multiplier
        _effective_west_radiation = _effective_radiation * west_multiplier
        
        _active_directions = []
        if south_multiplier > 0.0: _active_directions.append("S")
        if west_multiplier > 0.0: _active_directions.append("W")
        activeMsg = u" • {}".format("+".join(_active_directions)) if len(_active_directions) > 0 else u""
        
        sunElevationMsg = round( elevation, 1 )
        sunAzimutMsg = round( azimut, 1 )
      
        min_elevationMsg = u" (min {})".format( round( min_elevation,1) ) if min_elevation > 0 else ""
        
        debug_info = { "azimut": sunAzimutMsg, "elevation": sunElevationMsg, "min_elevation": min_elevationMsg, "effective_radiation": round(_effective_radiation / 60.0, 1), "active": activeMsg }

        return _effective_south_radiation, _effective_west_radiation, _effective_radiation, debug_info

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
