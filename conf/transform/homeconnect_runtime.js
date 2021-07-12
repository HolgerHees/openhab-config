(function(i) {
    if( i == "-" || i == "NULL" || i == 0 ) return "0 min.";
 
    /*var result = i.match(/[^T]*T([^Z]*)Z/i);
    var data = result[1].split(":");
    i = data[0] * 60 * 60;
    i += data[1] * 60;
    if( data.length > 2 )
    {
        i += data[2] * 60;
    }*/
    
    return Math.round(i / 60) + " min.";
})(input)
