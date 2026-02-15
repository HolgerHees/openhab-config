import math

from scope import actions

astroAction = actions.get("astro","astro:sun:local")

# https://azimut.polka-umwelt.de/
# https://www.sonnenverlauf.de/
horizon_slots = [
    { "azimut":   0.00,  "elevation_map": { 30.0: { 'all': 0.2 }                            } },   # Nachbar 1 (geradezu) - 15.0°
    { "azimut":  14.00,  "elevation_map": {  8.0: { 'all': 0.2 }, 11.0: { 'all': 0.3 }      } },   # Lücke - 8.0°
    { "azimut":  24.50,  "elevation_map": { 11.0: { 'all': 0.2 }                            } },   # Nachbar 2 - 11.0°
    { "azimut":  36.00,  "elevation_map": {  8.0: { 'all': 0.2 }, 11.0: { 'all': 0.3 }      } },   # Lücke - 8.0°
    { "azimut":  44.00,  "elevation_map": { 11.0: { 'all': 0.2 }                            } },   # Nachbar 3 - 11.0°
    { "azimut":  52.00,  "elevation_map": {  8.0: { 'all': 0.2 }, 11.0: { 'all': 0.3 }      } },   # Lücke - 8.0°
    { "azimut":  56.00,  "elevation_map": { 17.0: { 'all': 0.2 }                            } },   # Erster Großer Baum - 17.0
    { "azimut":  65.00,  "elevation_map": {  9.0: { 'all': 0.2 }, 17.0: { 'all': 0.3 }      } },   # Strasse - 9°
    { "azimut":  72.00,  "elevation_map": { 17.0: { 'all': 0.2 }                            } },   # Baumreihe bei Fam. Marder - 17.0°
    { "azimut":  84.00,  "elevation_map": { 17.0: { 'all': 0.2 }, 25.5: { 'all': 0.3, 'east': 0.7 } } },   # Zweiter Teil der Baumreihe bei Fam. Marder - 25.5°
    { "azimut":  99.00,  "elevation_map": { 10.0: { 'all': 0.2 }, 12.0: { 'all': 0.3 }      } },   # Lücke - 10.0°
    { "azimut": 102.00,  "elevation_map": { 12.0: { 'all': 0.2 }                            } },   # Lücke - 13.5°
    { "azimut": 111.50,  "elevation_map": { 12.0: { 'all': 0.2 }                            } },   # Lücke - 12.5°
    { "azimut": 120.50,  "elevation_map": { 10.0: { 'all': 0.2 }                            } },   # Lücke - 10.0°
    { "azimut": 126.00,  "elevation_map": {  8.0: { 'all': 0.2 }, 10.0: { 'all': 0.3 }      } },   # Lücke - 8.0°
    { "azimut": 131.00,  "elevation_map": { 10.0: { 'all': 0.2 }                            } },   # Lücke - 10.0°
    { "azimut": 137.50,  "elevation_map": {  8.0: { 'all': 0.2 }, 10.0: { 'all': 0.3 }      } },   # Lücke - 8.0°
    { "azimut": 152.00,  "elevation_map": { 12.5: { 'all': 0.2 }                            } },   # Große Tanne links von Brendel - 12.5°
    { "azimut": 159.00,  "elevation_map": { 10.0: { 'all': 0.2 }, 12.5: { 'all': 0.3 }      } },   # Nachbar (Brendel) - 10.0°
    { "azimut": 173.00,  "elevation_map": { 12.5: { 'all': 0.2 }                            } },   # Nachbar (hinten) - 12.5°
    { "azimut": 192.00,  "elevation_map": { 18.0: { 'all': 0.2 }                            } },   # Große Tanne hinten rechts - 18.0°
    { "azimut": 203.00,  "elevation_map": { 15.5: { 'all': 0.2 }                            } }    # 10.5°

    # { "azimut":   0.00,  "elevation_map": { 30.0: 0.2               } },   # Nachbar 1 (geradezu) - 15.0°
    # { "azimut":  14.00,  "elevation_map": {  8.0: 0.2, 11.0: 0.3    } },   # Lücke - 8.0°
    # { "azimut":  24.50,  "elevation_map": { 11.0: 0.2               } },   # Nachbar 2 - 11.0°
    # { "azimut":  36.00,  "elevation_map": {  8.0: 0.2, 11.0: 0.3    } },   # Lücke - 8.0°
    # { "azimut":  44.00,  "elevation_map": { 11.0: 0.2               } },   # Nachbar 3 - 11.0°
    # { "azimut":  52.00,  "elevation_map": {  8.0: 0.2, 11.0: 0.3    } },   # Lücke - 8.0°
    # { "azimut":  56.00,  "elevation_map": { 17.0: 0.2               } },   # Erster Großer Baum - 17.0
    # { "azimut":  65.00,  "elevation_map": {  9.0: 0.2, 17.0: 0.3    } },   # Strasse - 9°
    # { "azimut":  72.00,  "elevation_map": { 17.0: 0.2               } },   # Baumreihe bei Fam. Marder - 17.0°
    # { "azimut":  86.00,  "elevation_map": { 17.0: 0.2, 25.5: 0.4    } },   # Zweiter Teil der Baumreihe bei Fam. Marder - 25.5°
    # { "azimut":  99.00,  "elevation_map": { 10.0: 0.2, 12.0: 0.3    } },   # Lücke - 10.0°
    # { "azimut": 102.00,  "elevation_map": { 12.0: 0.2               } },   # Lücke - 13.5°
    # { "azimut": 111.50,  "elevation_map": { 12.0: 0.2               } },   # Lücke - 12.5°
    # { "azimut": 120.50,  "elevation_map": { 10.0: 0.2               } },   # Lücke - 10.0°
    # { "azimut": 126.00,  "elevation_map": {  8.0: 0.2, 10.0: 0.3    } },   # Lücke - 8.0°
    # { "azimut": 131.00,  "elevation_map": { 10.0: 0.2               } },   # Lücke - 10.0°
    # { "azimut": 137.50,  "elevation_map": {  8.0: 0.2, 10.0: 0.3    } },   # Lücke - 8.0°
    # { "azimut": 152.00,  "elevation_map": { 12.5: 0.2               } },   # Große Tanne links von Brendel - 12.5°
    # { "azimut": 159.00,  "elevation_map": { 10.0: 0.2, 12.5: 0.3    } },   # Nachbar (Brendel) - 10.0°
    # { "azimut": 173.00,  "elevation_map": { 12.5: 0.2               } },   # Nachbar (hinten) - 12.5°
    # { "azimut": 192.00,  "elevation_map": { 18.0: 0.2               } },   # Große Tanne hinten rechts - 18.0°
    # { "azimut": 203.00,  "elevation_map": { 15.5: 0.2               } }    # 10.5°

#    { "azimut":   0.00,  "elevation_map": { 15.0: 0.0, 30.0: 0.5 } },   # Nachbar 1 (geradezu)
#    { "azimut":  14.00,  "elevation_map": {  6.0: 0.0,  8.0: 0.1, 12.0: 0.2 } },
#    { "azimut":  24.50,  "elevation_map": { 11.0: 0.0, 12.0: 0.1 } },   # Nachbar 2
#    { "azimut":  36.00,  "elevation_map": {  6.0: 0.0,  8.0: 0.1, 12.0: 0.2 } },
#    { "azimut":  44.00,  "elevation_map": { 11.0: 0.0, 12.0: 0.1 } },   # Nachbar 3
#    { "azimut":  52.00,  "elevation_map": {  6.0: 0.0,  8.0: 0.1, 12.0: 0.2 } },
#    { "azimut":  56.00,  "elevation_map": { 17.0: 0.0, 19.2: 0.1 } },   # Erster Großer Baum
#    { "azimut":  65.00,  "elevation_map": {  8.0: 0.0,  9.0: 0.1, 14.0: 0.2 } },   # Strasse
#    { "azimut":  72.00,  "elevation_map": { 13.0: 0.0, 22.0: 0.1, 23.0: 0.2 } },   # Baumreihe bei Fam. Marder
#    { "azimut":  86.00,  "elevation_map": { 25.5: 0.0, 27.5: 0.1 } },   # Zweiter Teil der Baumreihe bei Fam. Marder
#    { "azimut":  99.00,  "elevation_map": {  8.0: 0.0, 10.0: 0.1, 12.0: 0.2, 16.0: 0.3 } },
#    { "azimut": 102.00,  "elevation_map": { 11.5: 0.0, 13.5: 0.1, 15.5: 0.2, 17.5: 0.3 } },
#    { "azimut": 111.50,  "elevation_map": { 10.5: 0.0, 12.5: 0.1, 14.5: 0.2, 16.5: 0.3 } },
#    { "azimut": 120.50,  "elevation_map": {  8.0: 0.0, 10.0: 0.1, 12.0: 0.2, 16.0: 0.3 } },
#    { "azimut": 126.00,  "elevation_map": {  6.0: 0.0,  8.0: 0.1 } },
#    { "azimut": 131.00,  "elevation_map": {  8.0: 0.0, 10.0: 0.1 } },
#    { "azimut": 137.50,  "elevation_map": {  6.0: 0.0,  8.0: 0.1 } },
#    { "azimut": 152.00,  "elevation_map": { 10.5: 0.0, 12.5: 0.1 } },   # Große Tanne links von Brendel
#    { "azimut": 159.00,  "elevation_map": {  8.0: 0.0, 10.0: 0.1 } },   # Nachbar (Brendel)
#    { "azimut": 173.00,  "elevation_map": { 12.5: 0.0, 12.5: 0.1 } },   # Nachbar (hinten)
#    { "azimut": 192.00,  "elevation_map": { 18.0: 0.0, 20.0: 0.1 } },   # Große Tanne hinten rechts
#    { "azimut": 203.00,  "elevation_map": { 10.5: 0.0, 12.5: 0.1 } }
]

# Inkscape ist 0 Grad rechts, also Osten
# Astro Binding fängt oben im Norden an
# d.h. die Inkscape Gradzahlen müssen + 90 Grad gerechnen werden

class SunRadiation():
    # haus um 3.2 grad gedreht
    # 3.2492105921044496
    AZIMUT_GARDEN_DEVIATION  = 3.3

    DIRECTION_EAST = "east"
    DIRECTION_SOUTH = "south"
    DIRECTION_WEST = "west"

    total_time1 = 0
    total_time2 = 0

    @staticmethod
    def getElevationFactor( time, direction = None ):
        azimut, elevation, min_elevation, min_factor = SunRadiation.getSunData(time, direction)
        return [min_factor if elevation <= min_elevation else 1.0, azimut]

    @staticmethod
    def getSunData( time, direction = None ):
        elevation, azimut = astroAction.getElevation(time).doubleValue(), astroAction.getAzimuth(time).doubleValue()

        active_horizon_slot = horizon_slots[0]
        for horizon_slot in horizon_slots:
            if azimut < horizon_slot["azimut"] + 90.0:
                break;
            active_horizon_slot = horizon_slot

        elevation_slot = [0,0]
        for _elevation, _factor_map in active_horizon_slot["elevation_map"].items():
            _factor = _factor_map[direction] if direction in _factor_map else _factor_map['all']

            if direction is not None and direction == SunRadiation.DIRECTION_SOUTH:
                _elevation += 3.0
                _factor = _factor * 0.5

            if elevation <= _elevation:
                elevation_slot = [_elevation, _factor]

        return azimut, elevation, elevation_slot[0], elevation_slot[1]

    @staticmethod
    def getSunPowerPerHour( reference_time, cloud_cover, sun_radiation = None ):

        azimut, elevation, min_elevation, _ = SunRadiation.getSunData( reference_time )
        
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
            if azimut >= _start and azimut <= _end:
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
