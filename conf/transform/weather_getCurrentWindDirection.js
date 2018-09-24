(function(i) {
	var data = JSON.parse(i);
	
    var windDirection = data.forecasts[0].windDirectionInDegree;
    
    if( windDirection >= 22.5 && windDirection < 67.5 ) return "Nordost";
    if( windDirection >= 67.5 && windDirection < 112.5 ) return "Ost";
    if( windDirection >= 112.5 && windDirection < 157.5 ) return "Südost";
    if( windDirection >= 157.5 && windDirection < 202.5 ) return "Süd";
    if( windDirection >= 202.5 && windDirection < 247.5 ) return "Südwest";
    if( windDirection >= 247.5 && windDirection < 292.5 ) return "West";
    if( windDirection >= 292.5 && windDirection < 337.5 ) return "Nordwest";
    if( windDirection >= 337.5 || windDirection < 22.5 ) return "Nord";

    return "";
})(input)
