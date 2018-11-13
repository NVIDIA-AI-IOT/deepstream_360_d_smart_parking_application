"use strict";

// A websocket client to test if the websocket is functioning as intended.
// It reads the config from config.json and sends the initial message to server.
// It then console logs the messages that it receives from the websocket.

var logger = require('winston');
var deepcopy = require("deepcopy");
const config=require('../config/config.json');

const hostIpAddress=process.env.IP_ADDRESS;
const backendPort=process.env.NODE_PORT;

const WS_HOST= "ws://"+hostIpAddress+":"+backendPort;
const webSocket = require('ws');

const ws = new webSocket(WS_HOST, {
    perMessageDeflate: false
});


ws.on('open', function () {
    logger.info("[ON OPEN] Opened conn");
    let configObj = deepcopy(config);
    let apiMode=null;
    let webSocketStartTimestamp=null;
    if(configObj.garage.isLive){
        apiMode="live";
        webSocketStartTimestamp=new Date().toISOString();
    }else{
        apiMode="playback";
        webSocketStartTimestamp=configObj.garage.playback.webSocket.startTimestamp;
    }
    let garageId=configObj.garage[apiMode].webSocket.garageId;
    let garageLevel=configObj.garage[apiMode].webSocket.garageLevel;
    let uiDelaySeconds=configObj.garage[apiMode].apis.uiDelaySeconds;
    let delayedStartTimestamp=new Date(Date.parse(webSocketStartTimestamp)-(uiDelaySeconds*1000)).toISOString();;
    var msg = { startTimestamp: delayedStartTimestamp, garageLevel: garageLevel, garageId: garageId }
    ws.send(JSON.stringify(msg), function ack(error) {
        if (error) {
            logger.info("[RECV UPDATES] Unable to send. Closing connection")
        }
    });
});

ws.on('close', function () {
    logger.info('Disconnected');
});

ws.on('error', function (error) {
    logger.error("[ON ERR] Sorry connection cannot be opened: " + error);
});

ws.on('message', function (message) {
    try {
        var jsonMessage = JSON.parse(message);
        console.log(jsonMessage)
    } catch (e) {
        logger.error("[MSG ERROR] " + e);
        return;
    }
});
