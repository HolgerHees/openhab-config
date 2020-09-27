(function(i) {
    sec = Math.round(i % 60);
    min = Math.round((i / 60) % 60);
    hrs = Math.round((i / (60*60)) % 24);
    day = Math.round(i / (60*60*24));
    tage = "Tage";
    stunden = "Stunden";
    minuten = "Minuten";
    sekunden = "Sekunden";
    
    if(day==1) tage = "Tag";
    if(hrs==1) stunden = "Stunde";
    if(min==1) minuten = "Minute";
    if(sec==1) sekunden = "Sekunde";
       
    if (day==0)
    {
        if (hrs==0)
        {
            return min + " " + minuten + ", " + sec + " " +sekunden;
        }
        else
        {
            return hrs + " " + stunden + ", " + min + " " +minuten;
        }
    } 
    else 
    {
        return day + " " + tage + ", " + hrs + " " +stunden;
    } 
})(input)
