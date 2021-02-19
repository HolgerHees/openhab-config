(function(i) {
    if( i == "-" || i == "NULL" || i == 0 ) return "0 min.";
 
    return Math.round(i / 60) + " min.";
})(input)
