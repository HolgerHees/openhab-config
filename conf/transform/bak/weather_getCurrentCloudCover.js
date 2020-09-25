(function(i) {
    var data = JSON.parse(i);
	
    return data.forecasts[0].effectiveCloudCoverInOcta;
})(input)
