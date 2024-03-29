# -*- coding: utf-8 -*-
Cases = {
    "enabled": [
        # **** ERDGESCHOSS incl. Schuppen ****
        { "phrase": u"licht gäste bad an", "items": [["pGF_Guesttoilet_Light_Ceiling_Powered","ON"],["pGF_Guesttoilet_Light_Mirror_Powered","ON"]] },
        { "phrase": u"deckenlicht gäste bad aus", "items": [["pGF_Guesttoilet_Light_Ceiling_Powered","OFF"]] },
        { "phrase": u"steckdose gäste bad aus", "items": [["pGF_Guesttoilet_Socket_Powered","OFF"]] },
        { "phrase": u"wc radio gäste bad ein", "items": [["pGF_Guesttoilet_Socket_Powered","ON"]] },
        { "phrase": u"rollladen gäste bad runter", "items": [["pGF_Guesttoilet_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden gäste bad rauf", "items": [["pGF_Guesttoilet_Shutter_Control","UP"]] },
        { "phrase": u"wie warm ist es im gästeklo", "items": [["pGF_Guesttoilet_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie feucht ist es im gästeklo", "items": [["pGF_Guesttoilet_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"deckenlicht hwr aus", "items": [["pGF_Utilityroom_Light_Ceiling_Powered","OFF"]] },

        { "phrase": u"licht vorratsraum an", "items": [["pGF_Boxroom_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"wie kalt ist es im vorratsraum", "items": [["pGF_Boxroom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie ist die Luftfeuchtigkeit im vorratsraum", "items": [["pGF_Boxroom_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht küche aus", "items": [[ "pGF_Kitchen_Light_Ceiling_Brightness", "OFF" ],["pGF_Kitchen_Light_Cupboard_Powered","OFF"]] },
        { "phrase": u"licht küche 50%", "items": [[ "pGF_Kitchen_Light_Ceiling_Brightness", "50" ]] },
        { "phrase": u"schranklicht küche an", "items": [["pGF_Kitchen_Light_Cupboard_Powered","ON"]] },
        { "phrase": u"rollladen küche schliessen", "items": [["pGF_Kitchen_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden küche hoch", "items": [["pGF_Kitchen_Shutter_Control","UP"]] },

        { "phrase": u"licht wohnzimmer stehlampe an", "items": [["pGF_Livingroom_Light_Hue2_Color","ON"]] },
        { "phrase": u"wohnzimmer stehlampe an", "items": [["pGF_Livingroom_Light_Hue2_Color","ON"]] },
        { "phrase": u"wohnzimmer couch steckdose an", "items": [["pGF_Livingroom_Socket_Couch_Powered","ON"]] },
        { "phrase": u"licht wohnzimmer bassbox an", "items": [["pGF_Livingroom_Light_Hue1_Color","ON"]] },
        { "phrase": u"licht wohnzimmer couch indirekt an", "items": [["pGF_Livingroom_Light_Hue1_Color","ON"],["pGF_Livingroom_Light_Hue2_Color","ON"]] },
        { "phrase": u"licht wohnzimmer couch decke an", "items": [["pGF_Livingroom_Light_Couchtable_Brightness","ON"]] },
        { "phrase": u"licht wohnzimmer couch an", "items": [["pGF_Livingroom_Light_Hue1_Color","ON"],["pGF_Livingroom_Light_Hue2_Color","ON"],["pGF_Livingroom_Light_Couchtable_Brightness","ON"]] },
        { "phrase": u"wohnzimmer bassbox steckdose an", "items": [["pGF_Livingroom_Socket_Bassbox_Powered","ON"]] },
        { "phrase": u"wohnzimmer kamin steckdose an", "items": [["pGF_Livingroom_Socket_Fireplace_Powered","ON"]] },
        { "phrase": u"licht wohnzimmer esstisch aus", "items": [["pGF_Livingroom_Light_Diningtable_Brightness","OFF"]] },
        { "phrase": u"licht wohnzimmer indirekt 30%", "items": [["pGF_Livingroom_Light_Hue1_Color","30"],["pGF_Livingroom_Light_Hue2_Color","30"],["pGF_Livingroom_Light_Hue4_Color","30"],["pGF_Livingroom_Light_Hue5_Color","30"]] },
        { "phrase": u"licht wohnzimmer decke aus", "items": [["pGF_Livingroom_Light_Couchtable_Brightness","OFF"],["pGF_Livingroom_Light_Diningtable_Brightness","OFF"]] },
        { "phrase": u"licht wohnzimmer und steckdose bassbox an", "items": [["pGF_Livingroom_Light_Couchtable_Brightness","ON"],["pGF_Livingroom_Light_Diningtable_Brightness","ON"],["pGF_Livingroom_Light_Hue1_Color","ON"],["pGF_Livingroom_Light_Hue2_Color","ON"],["pGF_Livingroom_Light_Hue4_Color","ON"],["pGF_Livingroom_Light_Hue5_Color","ON"],["pGF_Livingroom_Socket_Bassbox_Powered","ON"]] },
        { "phrase": u"rollladen wohnzimmer schliessen", "items": [["pGF_Livingroom_Shutter_Terrace_Control","DOWN"],["pGF_Livingroom_Shutter_Couch_Control","DOWN"]] },
        { "phrase": u"rollläden wohnzimmer couch hoch", "items": [["pGF_Livingroom_Shutter_Couch_Control","UP"]] },
        { "phrase": u"rollläden wohnzimmer esstisch runter", "items": [["pGF_Livingroom_Shutter_Terrace_Control","DOWN"]] },
        { "phrase": u"rollläden wohnzimmer terasse runter", "items": [["pGF_Livingroom_Shutter_Terrace_Control","DOWN"]] },
        { "phrase": u"wie warm ist es im wohnzimmer", "items": [["pGF_Livingroom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie trocken ist es im wohnzimmer", "items": [["pGF_Livingroom_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht gästezimmer an", "items": [["pGF_Workroom_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"licht bastelzimmer an", "items": [["pGF_Workroom_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"rollladen gästezimmer schliessen", "items": [["pGF_Workroom_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden gästezimmer hoch", "items": [["pGF_Workroom_Shutter_Control","UP"]] },
        { "phrase": u"wie warm ist es im gästezimmer", "items": [["pGF_Workroom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie feucht ist es im gästezimmer", "items": [["pGF_Workroom_Air_Sensor_Humidity_Value","READ"]] },

        # TODO should exclude upper floor light
        { "phrase": u"flur deckenlampe aus", "items": [["pFF_Corridor_Light_Ceiling_Powered","OFF"],["pGF_Corridor_Light_Ceiling_Powered","OFF"]] },
        { "phrase": u"flur spiegel licht aus", "items": [[ "pGF_Corridor_Light_Mirror_Powered", "OFF" ]] },
        { "phrase": u"flur indirekt aus", "items": [[ "pGF_Corridor_Light_Hue_Color", "OFF" ]] },
        # TODO should exclude upper floor light
        { "phrase": u"licht flur an", "items": [["pFF_Corridor_Light_Ceiling_Powered","ON"],["pGF_Corridor_Light_Ceiling_Powered","ON"],["pGF_Corridor_Light_Mirror_Powered","ON"],["pGF_Corridor_Light_Hue_Color","ON"]] },
        { "phrase": u"wie warm ist es im flur", "items": [["pGF_Corridor_Air_Sensor_Temperature_Value","READ"],["pFF_Corridor_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie warm ist es im flur unten", "items": [["pGF_Corridor_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie feucht ist es im flur unten", "items": [["pGF_Corridor_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"deckenlicht garage aus", "items": [["pGF_Garage_Light_Ceiling_Powered","OFF"]] },
        { "phrase": u"deckenlicht schuppen an", "items": [["pGF_Garage_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"licht schuppen an", "items": [["pGF_Garage_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"wie warm ist es im schuppen", "items": [["pGF_Garage_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie feucht ist es in der garage", "items": [["pGF_Garage_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht untergeschoss aus", "items": [["pGF_Livingroom_Light_Hue1_Color","OFF"],["pGF_Livingroom_Light_Hue2_Color","OFF"],["pGF_Livingroom_Light_Hue4_Color","OFF"],["pGF_Livingroom_Light_Hue5_Color","OFF"],["pGF_Corridor_Light_Ceiling_Powered","OFF"],["pGF_Boxroom_Light_Ceiling_Powered","OFF"],["pGF_Guesttoilet_Light_Mirror_Powered","OFF"],["pGF_Workroom_Light_Ceiling_Powered","OFF"],["pGF_Livingroom_Light_Couchtable_Brightness","OFF"],["pGF_Utilityroom_Light_Ceiling_Powered","OFF"],["pGF_Guesttoilet_Light_Ceiling_Powered","OFF"],["pGF_Kitchen_Light_Ceiling_Brightness","OFF"],["pGF_Kitchen_Light_Cupboard_Powered","OFF"],["pGF_Livingroom_Light_Diningtable_Brightness","OFF"],["pGF_Corridor_Light_Mirror_Powered","OFF"],["pGF_Corridor_Light_Hue_Color","OFF"],["pGF_Garage_Light_Ceiling_Powered","OFF"]] },        
        
        # **** OBERGESCHOSS incl. Dachboden ****

        { "phrase": u"licht bad aus", "items": [["pFF_Bathroom_Light_Mirror_Powered","OFF"],["pFF_Bathroom_Light_Ceiling_Powered","OFF"]] },
        { "phrase": u"deckenlicht badezimmer an", "items": [[ "pFF_Bathroom_Light_Ceiling_Powered", "ON" ]] },
        { "phrase": u"rollladen badezimmer schliessen", "items": [["pFF_Bathroom_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden badezimmer hoch", "items": [["pFF_Bathroom_Shutter_Control","UP"]] },
        { "phrase": u"wie warm ist es im bad", "items": [["pFF_Bathroom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie feucht ist es im bad", "items": [["pFF_Bathroom_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht ankleide an", "items": [["pFF_Dressingroom_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"rollladen ankleide schliessen", "items": [["pFF_Dressingroom_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden ankleide hoch", "items": [["pFF_Dressingroom_Shutter_Control","UP"]] },
        { "phrase": u"wie warm ist es in der ankleide", "items": [["pFF_Dressingroom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie feucht ist es in der ankleide", "items": [["pFF_Dressingroom_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht schlafzimmer bett links und decke an", "items": [[ "pFF_Bedroom_Light_Hue_Left_Color", "ON" ],[ "pFF_Bedroom_Light_Ceiling_Powered", "ON" ]] },
        { "phrase": u"licht schlafzimmer bett links und rechts an", "items": [[ "pFF_Bedroom_Light_Hue_Left_Color", "ON" ],[ "pFF_Bedroom_Light_Hue_Right_Color", "ON" ]] },
        { "phrase": u"deckenlicht schlafzimmer an", "items": [[ "pFF_Bedroom_Light_Ceiling_Powered", "ON" ]] },
        { "phrase": u"rollladen schlafzimmer schliessen", "items": [["pFF_Bedroom_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden schlafzimmer hoch", "items": [["pFF_Bedroom_Shutter_Control","UP"]] },
        { "phrase": u"wie warm ist es im schlafzimmer", "items": [["pFF_Bedroom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie trocken ist es im schlafzimmer", "items": [["pFF_Bedroom_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht sportzimmer an", "items": [["pFF_Fitnessroom_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"rollladen sportzimmer schliessen", "items": [["pFF_Fitnessroom_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden sportzimmer hoch", "items": [["pFF_Fitnessroom_Shutter_Control","UP"]] },
        { "phrase": u"wie warm ist es im sportzimmer", "items": [["pFF_Fitnessroom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie trocken ist es im sportzimmer zimmer", "items": [["pFF_Fitnessroom_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht schminkzimmer aus", "items": [["pFF_Makeuproom_Light_Ceiling_Powered","OFF"]] },
        { "phrase": u"rollladen schminkzimmer schliessen", "items": [["pFF_Makeuproom_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden schminkzimmer hoch", "items": [["pFF_Makeuproom_Shutter_Control","UP"]] },
        { "phrase": u"wie warm ist es im schminkzimmer", "items": [["pFF_Makeuproom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie trocken ist es im schminkzimmer zimmer", "items": [["pFF_Makeuproom_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht flur obergeschoss an", "items": [["pFF_Corridor_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"wie warm ist es im flur oben", "items": [["pFF_Corridor_Air_Sensor_Temperature_Value","READ"]] },

        { "phrase": u"licht dachboden an", "items": [["pFF_Attic_Light_Ceiling_Powered","ON"]] },
        { "phrase": u"steckdose dachboden aus", "items": [["pFF_Attic_Socket_Powered","OFF"]] },
        { "phrase": u"rollladen dachboden schliessen", "items": [["pFF_Attic_Shutter_Control","DOWN"]] },
        { "phrase": u"rollläden dachboden hoch", "items": [["pFF_Attic_Shutter_Control","UP"]] },
        { "phrase": u"wie kalt ist es auf dem dachboden", "items": [["pFF_Attic_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie trocken ist es auf dem dachboden", "items": [["pFF_Attic_Air_Sensor_Humidity_Value","READ"]] },

        { "phrase": u"licht obergeschoss an", "items": [["pFF_Bathroom_Light_Mirror_Powered","ON"],["pFF_Dressingroom_Light_Ceiling_Powered","ON"],["pFF_Bedroom_Light_Ceiling_Powered","ON"],["pFF_Corridor_Light_Ceiling_Powered","ON"],["pFF_Makeuproom_Light_Ceiling_Powered","ON"],["pFF_Bedroom_Light_Hue_Right_Color","ON"],["pFF_Bedroom_Light_Hue_Left_Color","ON"],["pFF_Bathroom_Light_Ceiling_Powered","ON"],["pFF_Fitnessroom_Light_Ceiling_Powered","ON"],["pFF_Attic_Light_Ceiling_Powered","ON"]] },

        # **** Draussen (Garten) ****
        
        { "phrase": u"aussenlicht schuppen vorne an", "items": [["pOutdoor_Streedside_Garage_Light_Powered","ON"]] },
        { "phrase": u"aussenlicht haustür an", "items": [["pOutdoor_Streedside_Frontdoor_Light_Powered","ON"]] },
        { "phrase": u"aussenlicht carport an", "items": [["pOutdoor_Carport_Light_Powered","ON"]] },
        { "phrase": u"aussenlicht terasse an", "items": [["pOutdoor_Terrace_Light_Brightness","ON"],["pOutdoor_Terrace_Light_Hue_Left_Color","ON"],["pOutdoor_Terrace_Light_Hue_Right_Color","ON"]] },
        { "phrase": u"aussenlicht schuppen hinten an", "items": [["pOutdoor_Garden_Garage_Light_Powered","ON"]] },
        { "phrase": u"aussen licht schuppen aus", "items": [["pOutdoor_Garden_Garage_Light_Powered","OFF"],["pOutdoor_Streedside_Garage_Light_Powered","OFF"]] },

        { "phrase": u"aussensteckdosen vorne an", "items": [[ "pOutdoor_Streeside_Socket_Powered", "ON" ]] },
        { "phrase": u"aussensteckdosen hinten aus", "items": [[ "pOutdoor_Terrace_Socket_Powered", "OFF" ]] },
        { "phrase": u"aussensteckdosen an", "items": [["pOutdoor_Toolshed_Socket_Powered","ON"],[ "pOutdoor_Streeside_Socket_Powered", "ON" ],[ "pOutdoor_Terrace_Socket_Powered", "ON" ]] },
        { "phrase": u"steckdosen draussen aus", "items": [["pOutdoor_Toolshed_Socket_Powered","OFF"],[ "pOutdoor_Streeside_Socket_Powered", "OFF" ],[ "pOutdoor_Terrace_Socket_Powered", "OFF" ]] },
        
        { "phrase": u"wie kalt ist es im garten", "items": [["pOutdoor_WeatherStation_Temperature","READ"]] },
        { "phrase": u"wie ist die luftfeuchtigkeit im garten", "items": [["pOutdoor_WeatherStation_Humidity","READ"]] },
        
        # **** HUE COLOR LIGHTS ****
        { "phrase": u"farbtemperatur wohnzimmer stehlampe warmweiss", "items": [["pGF_Livingroom_Light_Hue2_Temperature","100"]] },
        { "phrase": u"farbtemperatur wohnzimmer stehlampe 50%", "items": [["pGF_Livingroom_Light_Hue2_Temperature","50"]] },
        { "phrase": u"farbtemperatur wohnzimmer kaltweiß", "items": [["pGF_Livingroom_Light_Hue5_Temperature","0"],["pGF_Livingroom_Light_Hue4_Temperature","0"],["pGF_Livingroom_Light_Hue2_Temperature","0"],["pGF_Livingroom_Light_Hue1_Temperature","0"]] },
        
        { "phrase": u"licht wohnzimmer stehlampe rot", "items": [["pGF_Livingroom_Light_Hue2_Color","0,100,100"]] },
        { "phrase": u"wohnzimmer farbe blau", "items": [["pGF_Livingroom_Light_Hue4_Color","240,100,100"],["pGF_Livingroom_Light_Hue1_Color","240,100,100"],["pGF_Livingroom_Light_Hue5_Color","240,100,100"],["pGF_Livingroom_Light_Hue2_Color","240,100,100"]] },
        { "phrase": u"wohnzimmer lichtfarbe grün", "items": [["pGF_Livingroom_Light_Hue4_Color","120,100,50"],["pGF_Livingroom_Light_Hue1_Color","120,100,50"],["pGF_Livingroom_Light_Hue5_Color","120,100,50"],["pGF_Livingroom_Light_Hue2_Color","120,100,50"]] },

        # **** Sonstiges ****
        
        { "phrase": u"gute nacht", "items": [[ "pOther_Scene4", "ON" ]] },

        # **** Opener Questions ****
        { "phrase": u"ist das fenster im wohnzimmer offen", "items": [["pGF_Livingroom_Openingcontact_Window_Couch_State","READ"],["pGF_Livingroom_Openingcontact_Window_Terrace_State","READ"]] },
        { "phrase": u"sind die fenster im wohnzimmer offen", "items": [["pGF_Livingroom_Openingcontact_Window_Couch_State","READ"],["pGF_Livingroom_Openingcontact_Window_Terrace_State","READ"]] },
        { "phrase": u"ist das terassen fenster im wohnzimmer offen", "items": [["pGF_Livingroom_Openingcontact_Window_Terrace_State","READ"]] },
        #{ "phrase": u"welche fenster sind offen", "items": [] },
        #{ "phrase": u"welches fenster ist offen", "items": [] },
        #{ "phrase": u"welche türen sind offen", "items": [] },
        #{ "phrase": u"welche tür ist offen", "items": [] },
        
        # **** Opener Questions ****
        { "phrase": u"ist der rollladen im wohnzimmer offen", "items": [["pGF_Livingroom_Shutter_Terrace_Control","READ"],["pGF_Livingroom_Shutter_Couch_Control","READ"]] },
        { "phrase": u"ist der terassen rollladen im wohnzimmer offen", "items": [["pGF_Livingroom_Shutter_Terrace_Control","READ"]] },
        
        # **** LIGHT QUESTIONS ****
        { "phrase": u"ist das couch deckenlicht im wohnzimmer an", "items": [["pGF_Livingroom_Light_Couchtable_Brightness","READ"]] },
        { "phrase": u"ist das flur spiegel licht an", "items": [["pGF_Corridor_Light_Mirror_Powered","READ"]] },
        
        # **** percentage check ****

        { "phrase": u"licht küche 50% prozent", "items": [[ "pGF_Kitchen_Light_Ceiling_Brightness", "50" ]] },
        { "phrase": u"licht küche fünfzig prozent", "items": [[ "pGF_Kitchen_Light_Ceiling_Brightness", "50" ]] },
        { "phrase": u"licht wohnzimmer indirekt x prozent", "items": [], "is_valid": False },
        
        # **** FALSE POSITIVES ****
        
        { "phrase": u"wie warm ist es im schlafzimmer und in der küche", "items": [[ "pFF_Bedroom_Air_Sensor_Temperature_Value", "READ" ]], "is_valid": False },
        { "phrase": u"flur obergeschoss 50%", "items": [], "is_valid": False },

        # **** CLIENT ID BASED ****

        { "phrase": u"wohnzimmer stehlampe unten aus", "items": [["pGF_Livingroom_Light_Hue2_Color","OFF"]]},
        { "phrase": u"stehlampe unten aus", "client_id": "amzn1.ask.device.AFUSC2ZJY7NS7773FR5SXTQXXG626RYY2QYBY3TCA5IYYH7DMKPCVRSAW5MSX727ZVVGHPN4MJ3WDKA7NDIS5GDVSKM64OXUEFVRTLJRRJVKZFYHJ3ZK5EX35XQL5C4VXQUZ54TDDFM2GZLD2R7OIYURXSCQYNYGY2EBHC57ON5JGKN3CI2KE", "items": [["pGF_Livingroom_Light_Hue2_Color","OFF"]] },
        { "phrase": u"licht decken lampe aus", "client_id": "amzn1.ask.device.AFUSC2ZJY7NS7773FR5SXTQXXG626RYY2QYBY3TCA5IYYH7DMKPCVRSAW5MSX727ZVVGHPN4MJ3WDKA7NDIS5GDVSKM64OXUEFVRTLJRRJVKZFYHJ3ZK5EX35XQL5C4VXQUZ54TDDFM2GZLD2R7OIYURXSCQYNYGY2EBHC57ON5JGKN3CI2KE", "items": [["pGF_Livingroom_Light_Diningtable_Brightness","OFF"],["pGF_Livingroom_Light_Couchtable_Brightness","OFF"]] },
        
        
        { "phrase": u"steckdose bassbox aus", "client_id": "amzn1.ask.device.AFUSC2ZJY7NS7773FR5SXTQXXG626RYY2QYBY3TCA5IYYH7DMKPCVRSAW5MSX727ZVVGHPN4MJ3WDKA7NDIS5GDVSKM64OXUEFVRTLJRRJVKZFYHJ3ZK5EX35XQL5C4VXQUZ54TDDFM2GZLD2R7OIYURXSCQYNYGY2EBHC57ON5JGKN3CI2KE", "items": [["pGF_Livingroom_Socket_Bassbox_Powered","OFF"]] },
        { "phrase": u"licht flur oben an und küche 50%", "client_id": "amzn1.ask.device.AFUSC2ZJY7NS7773FR5SXTQXXG626RYY2QYBY3TCA5IYYH7DMKPCVRSAW5MSX727ZVVGHPN4MJ3WDKA7NDIS5GDVSKM64OXUEFVRTLJRRJVKZFYHJ3ZK5EX35XQL5C4VXQUZ54TDDFM2GZLD2R7OIYURXSCQYNYGY2EBHC57ON5JGKN3CI2KE", "items": [["pFF_Corridor_Light_Ceiling_Powered","ON"],["pGF_Kitchen_Light_Ceiling_Brightness","50"]] },
        
        # **** Kombiniert ****
        
        { "phrase": u"licht flur oben und wohnzimmer an", "items": [[ "pGF_Livingroom_Light_Hue4_Color", "ON" ],[ "pGF_Livingroom_Light_Hue5_Color", "ON" ],[ "pGF_Livingroom_Light_Hue1_Color", "ON" ],[ "pGF_Livingroom_Light_Hue2_Color", "ON" ],[ "pGF_Livingroom_Light_Couchtable_Brightness", "ON" ],[ "pGF_Livingroom_Light_Diningtable_Brightness", "ON" ],[ "pFF_Corridor_Light_Ceiling_Powered", "ON" ]] },
        { "phrase": u"licht flur oben und wohnzimmer und küche an", "items": [[ "pGF_Livingroom_Light_Hue4_Color", "ON" ],[ "pGF_Livingroom_Light_Hue5_Color", "ON" ],[ "pGF_Livingroom_Light_Hue1_Color", "ON" ],[ "pGF_Livingroom_Light_Hue2_Color", "ON" ],[ "pGF_Livingroom_Light_Couchtable_Brightness", "ON" ],[ "pGF_Livingroom_Light_Diningtable_Brightness", "ON" ],[ "pFF_Corridor_Light_Ceiling_Powered", "ON" ],[ "pGF_Kitchen_Light_Ceiling_Brightness", "ON" ],[ "pGF_Kitchen_Light_Cupboard_Powered", "ON" ]] },
        { "phrase": u"licht wohnzimmer und küche 50%", "items": [[ "pGF_Livingroom_Light_Hue4_Color", "50" ],[ "pGF_Livingroom_Light_Hue5_Color", "50" ],[ "pGF_Livingroom_Light_Hue1_Color", "50" ],[ "pGF_Livingroom_Light_Hue2_Color", "50" ],[ "pGF_Livingroom_Light_Couchtable_Brightness", "50" ],[ "pGF_Livingroom_Light_Diningtable_Brightness", "50" ],[ "pGF_Kitchen_Light_Ceiling_Brightness", "50" ]] },
        { "phrase": u"licht wohnzimmer 50% und küche an", "items": [[ "pGF_Livingroom_Light_Hue4_Color", "50" ],[ "pGF_Livingroom_Light_Hue5_Color", "50" ],[ "pGF_Livingroom_Light_Hue1_Color", "50" ],[ "pGF_Livingroom_Light_Hue2_Color", "50" ],[ "pGF_Livingroom_Light_Couchtable_Brightness", "50" ],[ "pGF_Livingroom_Light_Diningtable_Brightness", "50" ],[ "pGF_Kitchen_Light_Ceiling_Brightness", "ON" ],[ "pGF_Kitchen_Light_Cupboard_Powered", "ON" ]] },
        { "phrase": u"licht wohnzimmer an und rollladen küche runter", "items": [[ "pGF_Livingroom_Light_Hue4_Color", "ON" ],[ "pGF_Livingroom_Light_Hue5_Color", "ON" ],[ "pGF_Livingroom_Light_Hue1_Color", "ON" ],[ "pGF_Livingroom_Light_Hue2_Color", "ON" ],[ "pGF_Livingroom_Light_Couchtable_Brightness", "ON" ],[ "pGF_Livingroom_Light_Diningtable_Brightness", "ON" ],[ "pGF_Kitchen_Shutter_Control", "DOWN" ]] },
        { "phrase": u"licht wohnzimmer und flur an und dachboden und bad rollläden runter", "items": [[ "pGF_Livingroom_Light_Hue4_Color", "ON" ],[ "pGF_Corridor_Light_Ceiling_Powered", "ON" ],[ "pGF_Livingroom_Light_Hue5_Color", "ON" ],[ "pFF_Corridor_Light_Ceiling_Powered", "ON" ],[ "pGF_Livingroom_Light_Hue1_Color", "ON" ],[ "pGF_Livingroom_Light_Couchtable_Brightness", "ON" ],[ "pGF_Livingroom_Light_Diningtable_Brightness", "ON" ],[ "pGF_Livingroom_Light_Hue2_Color", "ON" ],[ "pGF_Corridor_Light_Mirror_Powered", "ON" ],[ "pGF_Corridor_Light_Hue_Color", "ON" ],[ "pFF_Bathroom_Shutter_Control", "DOWN" ],[ "pFF_Attic_Shutter_Control", "DOWN" ]] },
        { "phrase": u"alle licht aus und rollläden komplett runter", "items": [["pGF_Guesttoilet_Light_Ceiling_Powered","OFF"],["pGF_Guesttoilet_Light_Mirror_Powered","OFF"],["pGF_Utilityroom_Light_Ceiling_Powered","OFF"],["pGF_Boxroom_Light_Ceiling_Powered","OFF"],["pGF_Kitchen_Light_Ceiling_Brightness","OFF"],["pGF_Kitchen_Light_Cupboard_Powered","OFF"],["pGF_Livingroom_Light_Diningtable_Brightness","OFF"],["pGF_Livingroom_Light_Hue4_Color","OFF"],["pGF_Livingroom_Light_Hue5_Color","OFF"],["pGF_Livingroom_Light_Hue1_Color","OFF"],["pGF_Livingroom_Light_Hue2_Color","OFF"],["pGF_Livingroom_Light_Couchtable_Brightness","OFF"],["pGF_Workroom_Light_Ceiling_Powered","OFF"],["pGF_Corridor_Light_Hue_Color","OFF"],["pGF_Corridor_Light_Mirror_Powered","OFF"],["pGF_Corridor_Light_Ceiling_Powered","OFF"],["pGF_Garage_Light_Ceiling_Powered","OFF"],["pFF_Bathroom_Light_Ceiling_Powered","OFF"],["pFF_Bathroom_Light_Mirror_Powered","OFF"],["pFF_Dressingroom_Light_Ceiling_Powered","OFF"],["pFF_Bedroom_Light_Hue_Right_Color","OFF"],["pFF_Bedroom_Light_Hue_Left_Color","OFF"],["pFF_Bedroom_Light_Ceiling_Powered","OFF"],["pFF_Fitnessroom_Light_Ceiling_Powered","OFF"],["pFF_Makeuproom_Light_Ceiling_Powered","OFF"],["pFF_Corridor_Light_Ceiling_Powered","OFF"],["pFF_Attic_Light_Ceiling_Powered","OFF"],["pGF_Guesttoilet_Shutter_Control","DOWN"],["pGF_Kitchen_Shutter_Control","DOWN"],["pGF_Livingroom_Shutter_Terrace_Control","DOWN"],["pGF_Livingroom_Shutter_Couch_Control","DOWN"],["pGF_Workroom_Shutter_Control","DOWN"],["pFF_Bathroom_Shutter_Control","DOWN"],["pFF_Dressingroom_Shutter_Control","DOWN"],["pFF_Bedroom_Shutter_Control","DOWN"],["pFF_Fitnessroom_Shutter_Control","DOWN"],["pFF_Makeuproom_Shutter_Control","DOWN"],["pFF_Attic_Shutter_Control","DOWN"]] },
        { "phrase": u"licht innen aus und rollläden obergeschoss runter", "items": [["pGF_Guesttoilet_Light_Ceiling_Powered","OFF"],["pGF_Guesttoilet_Light_Mirror_Powered","OFF"],["pGF_Utilityroom_Light_Ceiling_Powered","OFF"],["pGF_Boxroom_Light_Ceiling_Powered","OFF"],["pGF_Kitchen_Light_Ceiling_Brightness","OFF"],["pGF_Kitchen_Light_Cupboard_Powered","OFF"],["pGF_Livingroom_Light_Diningtable_Brightness","OFF"],["pGF_Livingroom_Light_Hue4_Color","OFF"],["pGF_Livingroom_Light_Hue5_Color","OFF"],["pGF_Livingroom_Light_Hue1_Color","OFF"],["pGF_Livingroom_Light_Hue2_Color","OFF"],["pGF_Livingroom_Light_Couchtable_Brightness","OFF"],["pGF_Workroom_Light_Ceiling_Powered","OFF"],["pGF_Corridor_Light_Hue_Color","OFF"],["pGF_Corridor_Light_Mirror_Powered","OFF"],["pGF_Corridor_Light_Ceiling_Powered","OFF"],["pGF_Garage_Light_Ceiling_Powered","OFF"],["pFF_Bathroom_Light_Ceiling_Powered","OFF"],["pFF_Bathroom_Light_Mirror_Powered","OFF"],["pFF_Dressingroom_Light_Ceiling_Powered","OFF"],["pFF_Bedroom_Light_Hue_Right_Color","OFF"],["pFF_Bedroom_Light_Hue_Left_Color","OFF"],["pFF_Bedroom_Light_Ceiling_Powered","OFF"],["pFF_Fitnessroom_Light_Ceiling_Powered","OFF"],["pFF_Makeuproom_Light_Ceiling_Powered","OFF"],["pFF_Corridor_Light_Ceiling_Powered","OFF"],["pFF_Attic_Light_Ceiling_Powered","OFF"],["pFF_Bathroom_Shutter_Control","DOWN"],["pFF_Dressingroom_Shutter_Control","DOWN"],["pFF_Bedroom_Shutter_Control","DOWN"],["pFF_Fitnessroom_Shutter_Control","DOWN"],["pFF_Makeuproom_Shutter_Control","DOWN"],["pFF_Attic_Shutter_Control","DOWN"]] },
        { "phrase": u"licht im wohnzimmer und aussen licht und steckdosen aus", "items": [["pOutdoor_Toolshed_Right_Light_Powered","OFF"],["pOutdoor_Toolshed_Socket_Powered","OFF"],["pGF_Livingroom_Light_Diningtable_Brightness","OFF"],["pGF_Livingroom_Light_Hue4_Color","OFF"],["pGF_Livingroom_Light_Hue5_Color","OFF"],["pGF_Livingroom_Light_Hue1_Color","OFF"],["pGF_Livingroom_Light_Hue2_Color","OFF"],["pGF_Livingroom_Light_Couchtable_Brightness","OFF"],["pOutdoor_Streedside_Garage_Light_Powered","OFF"],["pOutdoor_Streedside_Frontdoor_Light_Powered","OFF"],["pOutdoor_Carport_Light_Powered","OFF"],["pOutdoor_Garden_Garage_Light_Powered","OFF"],["pOutdoor_Terrace_Light_Brightness","OFF"],["pOutdoor_Terrace_Light_Hue_Left_Color","OFF"],["pOutdoor_Terrace_Light_Hue_Right_Color","OFF"],["pOutdoor_Streeside_Socket_Powered","OFF"],["pOutdoor_Terrace_Socket_Powered","OFF"]] },
        { "phrase": u"wie ist die temperatur im schlafzimmer und die luftfeuchtigkeit wohnzimmer", "items": [["pGF_Livingroom_Air_Sensor_Humidity_Value","READ"],["pFF_Bedroom_Air_Sensor_Temperature_Value","READ"]] },
        { "phrase": u"wie warm ist es im schlafzimmer und im wohnzimmer", "items": [["pFF_Bedroom_Air_Sensor_Temperature_Value","READ"],["pGF_Livingroom_Air_Sensor_Temperature_Value","READ"]] },
    ]
} 
