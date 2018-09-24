(function(i) {
    var data = JSON.parse(i);
	
	var reference = new Date ();
	reference.setHours ( reference.getHours() + 4 );
	reference.setMinutes(0);
	reference.setSeconds(0);
	
	for(var i = 0; i < data.forecasts.length; i++)
	{
		var forecast = data.forecasts[i];

		var hour = new Date(forecast.validFrom);
		
		if( reference.getTime() <= hour.getTime() )
		{
			return forecast.effectiveCloudCoverInOcta;
		}
	}

    return 0;
})(input)
