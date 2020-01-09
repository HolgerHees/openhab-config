function InitializedListener() 
{
    var isPhone = ( navigator.userAgent.indexOf("Android") != -1 && navigator.userAgent.indexOf("Mobile") != -1 );
    var theme = isPhone || parent.document.location.pathname.includes("habpanel") ? 'dark' : 'light';

    var timeRange;
    
    function getFromItem()
    {
        return "Chart_From";
    }

    function getTimerange(value)
    {
        return timeRange;
    }

    function getPanel(panel)
    {
        if( timeRange == "now-1h" || timeRange == "now-1d" ) return panel[0];
        
        if( timeRange == "now-1w" || timeRange == "now-1M" ) return panel[1];
        
        return panel[2];
    }

    this.generateParams = function( dashboard )
    {
        var self = this;
        var panel = [ arguments[1],arguments[2],arguments[3] ];
        
        var panelItemFunction = function(value)
        { 
            return getPanel(panel) 
        }
        
        return { dashboard: dashboard, theme: theme, panelItem: getFromItem(), panelItemFunction: panelItemFunction, fromItem: getFromItem(), fromItemFunction: getTimerange };
    }
    
    this.initIFrames = function ()
    {
        var iframes = document.getElementsByTagName("iframe");
        for( i = 0; i < iframes.length; i++ )
        {
            iframes[i].onload = function() {
                var cssLink = this.contentWindow.document.createElement("link");
                cssLink.href = "/static/grafana/css/grafana.css"; 
                cssLink.rel = "stylesheet"; 
                cssLink.type = "text/css"; 
                this.contentWindow.document.head.appendChild(cssLink);
            };
        }
    }
    
    smartHomeSubscriber.addItemListener(getFromItem(),function(item,state)
    {
        switch (state) {
            case "HOUR": 
                timeRange = "now-1h";
                break;
            case "DAY":
                timeRange = "now-1d";
                break;
            default: 
            case "WEEK":
                timeRange = "now-1w";
                break;
            case "MONTH":
                timeRange = "now-1M";
                break;
            case "YEAR":
                timeRange = "now-1y";
                break;
            case "5YEARS":
                timeRange = "now-5y";
                break;
        }
    });    
}
