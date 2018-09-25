
// the prefix that is used for each Grafana panel URL
SMARTHOME_GRAFANA_DEFAULTS["urlPrefix"] = "/grafana";

// use "false" so actual pages are loaded (or comment the line)
SMARTHOME_GRAFANA_DEFAULTS["debug"] = "false";

// use "default" for the default Eclipse SmartHome sitemap (or comment the line)
SMARTHOME_GRAFANA_DEFAULTS["sitemap"] = "default";

SMARTHOME_GRAFANA_DEFAULTS["theme"] = "dark";

if (SMARTHOME_GRAFANA_DEFAULTS["debug"] === "true") {
    console.log("Using SMARTHOME_GRAFANA_DEFAULTS = " + JSON.stringify(SMARTHOME_GRAFANA_DEFAULTS));
}
