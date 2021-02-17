(function(i) {
    var value = parseInt(i);
    if( value < 1048576 )
    {
        return Math.round(parseInt(i) / 1024) + " KBit";
    }
    return Math.round(parseInt(i) / 1024 / 1024) + " MBit";
})(input)
