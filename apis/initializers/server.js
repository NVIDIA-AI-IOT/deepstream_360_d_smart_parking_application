// Loading all the required libraries
var express = require('express');
var path = require('path');
const csv = require('csvtojson');
var bodyParser = require('body-parser');
var morgan = require('morgan');
var winston = require('winston');
var logger = winston.createLogger({
  transports: [
    new (winston.transports.Console)({ 'timestamp': true })
  ],
  exitOnError: false
});
var websocket = require('../app/ws/websocket')

//Loading config
const config=require('../config/config.json');

var app;

/** This method is used to read parking spot id from the parkingspot csv file */
var getParkingSpotDetails = function (configFile) {
  return new Promise(function (resolve, reject) {
    const csvFilePath = configFile
    var availabilityDict = {Total: 0 ,spotSet:null}
    csv()
      .fromFile(csvFilePath)
      .then((jsonObjList)=>{
        let formattedResults=jsonObjList.map(jsonObj => jsonObj['ParkingSpotId']);
        availabilityDict.spotSet=new Set(formattedResults);
        availabilityDict.Total=availabilityDict.spotSet.size;
        resolve({
          "availabilityDict": availabilityDict
        });
      })
      .catch(error=>{
        reject(error);
      });
  });
}

var start = function (cb) {
  'use strict';
  logger.info('[SERVER] Getting metadata of Parking Spots');
  getParkingSpotDetails(config.garage.backend.parkingSpotConfigFile).then(spotMetadata => {
    var statsGarage = require('../app/models/stats_model')
    let availabilityDict = {
      "Total": spotMetadata["availabilityDict"].Total,
      "spotSet":spotMetadata["availabilityDict"].spotSet
    }

    // setting availability Dict for stats api and websocket 
    statsGarage.init(availabilityDict);
    websocket.init(availabilityDict.spotSet);
    
    const socketServer = require('ws').Server;

    // Configure express 
    app = express();

    app.use(morgan('common'));
    app.use(bodyParser.urlencoded({ extended: true }));
    app.use(bodyParser.json({ type: '*/*' }));

    // Configure to allow CORS
    app.use(function (req, res, next) {
      res.setHeader("Access-Control-Allow-Origin", "*");
      res.setHeader("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Remote-User");
      next();
    });
    logger.info('[SERVER] Initializing routes');

    require('../app/routes/index')(app);

    app.use(express.static(path.join(__dirname, 'public')));

    // Error handler
    app.use(function (err, req, res, next) {
      res.status(err.status || 500);
      res.json({
        message: err.message,
        error: (app.get('env') === 'development' ? err : {})
      });
      next(err);
    });

    // Reads the port from environment variable
    var server = app.listen(process.env.NODE_PORT);
    logger.info('[SERVER] Listening on port ' + process.env.NODE_PORT);

    const wss = new socketServer({ server });
    //init Websocket ws and handle incoming connect requests
    wss.on('connection', function connection(ws) {
      logger.info('[CONN RECV] Received at: %s:%d', ws._socket.remoteAddress, ws._socket.remotePort)
      var intObj = null
      //on connect message
      ws.on('message', function incoming(message) {
        if (intObj != null) {
          // Stop the periodic transmission of existing stream
          clearInterval(intObj)
        }

        logger.info('[RECV] received: %s', message);

        try {
          message = JSON.parse(message)
          // Validating the initial message and handling error if any
          if (message.hasOwnProperty('startTimestamp') && message.hasOwnProperty('garageId') && message.hasOwnProperty('garageLevel')) {
            var startTimestamp = message['startTimestamp']
            var garageLevel = message['garageLevel']
            var garageId = message['garageId']
            // Calling the sendUpdates function of websocket because the initial data is valid
            intObj = websocket.sendUpdates(ws, startTimestamp, garageId, garageLevel)
          } else if (!message.hasOwnProperty('startTimestamp') && !message.hasOwnProperty('garageId') && !message.hasOwnProperty('garageLevel')) {
            logger.error('[SERVER ERROR] startTimestamp, garageId and garageLevel not present');
            ws.send(JSON.stringify({ error: " startTimestamp, garageId and garageLevel not present" }), function ack(err) {
              if (err) {
                logger.info("[SEND UPDATES] Unable to send error message to client that error has occurred: %s . Closing connection", JSON.stringify({ error: err }))
              }
            });
          } else if (!message.hasOwnProperty('startTimestamp')) {
            logger.error('[SERVER ERROR] startTimestamp not present');
            ws.send(JSON.stringify({ error: " startTimestamp not present" }), function ack(err) {
              if (err) {
                logger.info("[SEND UPDATES] Unable to send error message to client that error has occurred: %s . Closing connection", JSON.stringify({ error: err }))
              }
            });
          } else if (!message.hasOwnProperty('garageId')) {
            logger.error('[SERVER ERROR] garageId not present');
            ws.send(JSON.stringify({ error: " garageId not present" }), function ack(err) {
              if (err) {
                logger.info("[SEND UPDATES] Unable to send error message to client that error has occurred: %s . Closing connection", JSON.stringify({ error: err }))
              }
            });
          } else if (!message.hasOwnProperty('garageLevel')) {
            logger.error('[SERVER ERROR] garageLevel not present');
            ws.send(JSON.stringify({ error: " garageLevel not present" }), function ack(err) {
              if (err) {
                logger.info("[SEND UPDATES] Unable to send error message to client that error has occurred: %s . Closing connection", JSON.stringify({ error: err }))
              }
            });
          }
        }
        catch (error) {
          logger.error('[SERVER ERROR] Error: %s', error);
          ws.send(JSON.stringify({ error: error.toString() }), function ack(err) {
            if (err) {
              logger.info("[SEND UPDATES] Unable to send error message to client that error has occurred: %s . Closing connection", JSON.stringify({ error: err }))
            }
          });
        }

      });
      ws.on('error', (err) => {
        // Handle the error.
        logger.error('[SERVER CONN ERROR] Code:i %d', err.code)
        logger.error(err.code);
        logger.error(err);
      });
    });

    wss.on('error', (err) => {
      // Handle the error.
      logger.error('[SERVER ERROR] Code:i %d', err.code)
      logger.error(err.code);
      logger.error(err);
      logger.error(util.inspect(err, false, null));
    });
    if (cb) {
      return cb();
    }
  }).catch(err => {
    console.error(err);
  });
};

module.exports = start;