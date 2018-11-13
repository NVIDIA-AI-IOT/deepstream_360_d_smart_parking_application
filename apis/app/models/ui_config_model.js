'use strict';

// Loading required libraries and config file
var deepcopy = require("deepcopy");
const config=require('../../config/config.json')

module.exports = {
    /** Reads the config file and sets the url for backend after reading the environment variable and sends the config to UI*/
    getUiConfig: function (req, res, next) {
        let configObj = deepcopy(config);
        let apiMode=null;
        if(configObj.garage.isLive){
            delete configObj.garage.playback;
            apiMode="live";
        }else{
            delete configObj.garage.live;
            apiMode="playback";
        }
        delete configObj.garage.backend;
        let hostIpAddress=process.env.IP_ADDRESS;
        let backendPort=process.env.NODE_PORT;
        configObj.garage[apiMode].webSocket.url="ws://"+hostIpAddress+":"+backendPort;
        configObj.garage[apiMode].apis.baseurl="http://"+hostIpAddress+":"+backendPort;
        res.json(configObj);
    }
}