'use strict';

// Loading required libraries and config file
const cassandra = require('cassandra-driver');
var config = require('../../config/config.json');
var winston = require('winston');
var logger = winston.createLogger({
    transports: [
        new (winston.transports.Console)({ 'timestamp': true, level: 'error' })
    ],
    exitOnError: false
});

const cassandraHosts = config.garage.backend.cassandraHosts;
// Connection to Cassandra
const client = new cassandra.Client({ contactPoints: cassandraHosts, keyspace: config.garage.backend.cassandraKeyspace });

// Reading constants from config file
const IS_LIVE = config.garage.isLive;
const CLI_SEND_PERIOD_IN_MS = config.garage.backend.webSocketSendPeriodInMs; 
const SENSOR_TYPE=config.garage.backend.sensorType;

var spotSet;

/**  Calculates latitude of object*/
function getObjectLat(objectY) {
    const ORIGIN_LAT = config.garage.backend.originLat;
    var objectLat = ORIGIN_LAT - (360 * objectY * 0.001 / 40000)
    return objectLat
}

/** Calculates longitude of object */
function getObjectLon(objectX, objectLat) {
    const ORIGIN_LAT = config.garage.backend.originLat;
    const ORIGIN_LON = config.garage.backend.originLon;
    var objectLon = ORIGIN_LON - ((360 * objectX * 0.001) / (40000 * Math.cos((ORIGIN_LAT + objectLat) * Math.PI / 360)))
    return objectLon
}

/** Returns the required attributes of the car object in a particular format. */
function getFormattedCarObject(row, state, garageLevel) {
    var removed = (row.event.type === 'exit' || row.event.type === 'empty') ? 1 : 0;
    var objectX = row.object.coordinate.x
    var objectY = row.object.coordinate.y
    var objectLat = getObjectLat(objectY)
    var objectLon = getObjectLon(objectX, objectLat)
    var objId = row.object.id;
    var parkingSpot = ""
    if (state === "parked" || state === "empty") {
        parkingSpot = row['place']['parkingspot']['id']
    }
    var car = {
        timestamp: row.timestamp,
        color: row.object.vehicle.color,
        garageLevel: garageLevel,
        id: objId,
        licensePlate: row.object.vehicle.license,
        licenseState: row.object.vehicle.licensestate,
        orientation: row.object.orientation,
        parkingSpot: parkingSpot,
        sensorType: row.sensor.type,
        state: state,
        eventType: row.event.type,
        removed: removed,
        type: row.object.vehicle.type,
        x: objectX,
        y: objectY,
        lat: objectLat,
        lon: objectLon
    }
    return car
}

/** A generic function which receives a queryObject and uses it to obtain results from cassandra. The queryObject consists of the query and the params. */
function getResultsFromCassandra(queryObject){
    return new Promise(function (resolve, reject) {
        client.execute(queryObject['query'], queryObject['params'],{ prepare: true })
        .then(result => {
            resolve(result.rows);
        }).catch(error => {
            reject(error);
        });
    });
}

/** Generates the first cassandra parking spot query for live system */
function getParkingStateQuery(garageId,garageLevel){
    let spotStateQueryObject = {}
    spotStateQueryObject['query'] = "select timestamp, place, sensor, object, event from parkingSpotState where garageid=? and level=?";
    spotStateQueryObject['params'] = [garageId, garageLevel];
    return spotStateQueryObject;
}

/** Generates the first cassandra parking spot query for playback system */
function getParkingSpotPlaybackQueries(sensorType,garageId,garageLevel,currentTimestamp,startTimestamp){
    var queryList = []
    for (let spot of spotSet) {
        let parkingSpotQueryObject = {}
        if (IS_LIVE && config.garage.live.apis.uiDelaySeconds!==0) {
            parkingSpotQueryObject['query'] = "select timestamp, spotid, place, sensor, object, event from parkingSpotPlayback where garageid=:garageId and level=:garageLevel and sensortype=:sensorType and spotid=:spotId and timestamp <= :ts limit 1";
            parkingSpotQueryObject['params'] = [garageId, garageLevel, sensorType, spot, currentTimestamp];
        }else if(!IS_LIVE){
            parkingSpotQueryObject['query'] = "select timestamp, spotid, place, sensor, object, event from parkingSpotPlayback where garageid=:garageId and level=:garageLevel and sensortype=:sensorType and spotid=:spotId and timestamp >= :startTs and timestamp <= :currentTs limit 1";
            parkingSpotQueryObject['params'] = [garageId, garageLevel, sensorType, spot, startTimestamp, currentTimestamp];
        }
        queryList.push(parkingSpotQueryObject);
    }
    return(queryList);
}

/** Generates subsequent cassandra parking spot queries for live/playback system */
function getParkingSpotDeltaQuery(sensorType,garageId,garageLevel,previousTimestamp,currentTimestamp){
    let parkingSpotQueryObject = {}
    parkingSpotQueryObject['query'] = "select timestamp, place, sensor, object, event from parkingSpotDelta where garageid=? and level=? and sensortype=? and timestamp > ? and timestamp <= ?";
    parkingSpotQueryObject['params'] = [garageId, garageLevel, sensorType, previousTimestamp, currentTimestamp];
    return parkingSpotQueryObject;
}

/** Gets the resolved results and formats the car objects */
function getFormattedParkingResults(parkingResult,garageLevel){
    if (parkingResult['event']['type'] === 'parked') {
        var state = "parked"
        return(getFormattedCarObject(parkingResult, state, garageLevel));
    } else if (parkingResult['event']['type'] === 'empty') {
        var state = "empty"
        return(getFormattedCarObject(parkingResult, state, garageLevel));
    }
}

/** Used to decide which kind of parking spot query needs to be made */
function getParkingSpotResults(isDeltaParkingSpotQuery, garageId, garageLevel, previousTimestamp, currentTimestamp, startTimestamp) {
    return new Promise(function (resolve, reject) {
        if (!isDeltaParkingSpotQuery) {
            if (IS_LIVE && config.garage.live.apis.uiDelaySeconds===0) {
                let spotStateQueryObject=getParkingStateQuery(garageId,garageLevel);
                getResultsFromCassandra(spotStateQueryObject).then(spotStateList=>{
                    let formattedResults=spotStateList.map(parkingResult => getFormattedParkingResults(parkingResult,garageLevel));
                    resolve(formattedResults);
                }).catch(error=>{
                    reject(error);
                })
            }else{
                let queryObjectList=getParkingSpotPlaybackQueries(SENSOR_TYPE,garageId,garageLevel,currentTimestamp, startTimestamp);
                let playbackQueryList=queryObjectList.map(getResultsFromCassandra);
                Promise.all(playbackQueryList).then(playbackResultList=>{
                    let playbackResults=[].concat(...playbackResultList);
                    let formattedResults=playbackResults.map(parkingResult => getFormattedParkingResults(parkingResult,garageLevel));
                    resolve(formattedResults);
                }).catch(error=>{
                    reject(error);
                })
            }
        }else{
            let queryObject=getParkingSpotDeltaQuery(SENSOR_TYPE,garageId,garageLevel,previousTimestamp,currentTimestamp);
            getResultsFromCassandra(queryObject).then(deltaResults=>{
                let formattedResults=deltaResults.map(parkingResult => getFormattedParkingResults(parkingResult,garageLevel));
                resolve(formattedResults);
            }).catch(error=>{
                reject(error);
            });
        }
    });
}

/** Generates the cassandra aisle query for live/playback system  
 * and formats the results
*/
function getAisleResults(garageId, garageLevel, previousTimestamp, currentTimestamp) {
    return new Promise(function (resolve, reject) {
        let aisleQueryObject={}
        aisleQueryObject["query"]= "select messageid, timestamp, place, sensor, object, event from aisle where messageid=? and timestamp > ? and timestamp <= ?";
        aisleQueryObject["params"]=[garageId + "-" + garageLevel, previousTimestamp, currentTimestamp]
        getResultsFromCassandra(aisleQueryObject).then(aisleResultList=>{
            let formattedAisleResultList=[];
            for(let aisleResult of aisleResultList){
                var state = "moving";
                var car = getFormattedCarObject(aisleResult, state, garageLevel);
                formattedAisleResultList.push(car);
            }
            resolve(formattedAisleResultList);
        }).catch(error=>{
            reject(error);
        });
    });
}

/** Used to generate parkingspot and aisle results asynchronously */
function getResults(isDeltaParkingSpotQuery, garageId, garageLevel, previousTimestamp, currentTimestamp, startTimestamp) {
    return new Promise(function (resolve, reject) {
        let taskList=[]
        taskList.push(getParkingSpotResults(isDeltaParkingSpotQuery, garageId, garageLevel, previousTimestamp, currentTimestamp, startTimestamp));
        taskList.push(getAisleResults(garageId, garageLevel, previousTimestamp, currentTimestamp));
        Promise.all(taskList).then(results => {
            resolve({
                parkingSpotResults: results[0],
                movingResults: results[1]
            });
        }).catch(error => {
            reject(error);
        });
    });
}


/** Used to get the moving car dictionary */
function getMovingCarDict(movingResults) {
    var movingCarDict = {}
    for (let i = 0; i < movingResults.length; i++) {
        let car = movingResults[i];
        let eventTimestamp=car.timestamp;
        if (movingCarDict.hasOwnProperty(car['id'])) {
            if (new Date(eventTimestamp) >= movingCarDict[car['id']]['timestamp']) {
                movingCarDict[car['id']] = { timestamp: new Date(eventTimestamp), object: car }
            }
        } else {
            movingCarDict[car['id']] = { timestamp: new Date(eventTimestamp), object: car }
        }
    }
    return (movingCarDict);
}

/** Used to maintain state of moving cars so that it can be retired 
 *  after certain amount of time 
 */
function updateMovingCarState(movingResults,movingCarState){
    for (var i = 0; i < movingResults.length; i++) {
        var car = movingResults[i];
        var eventType = car.eventType;
        var eventTimestamp = car.timestamp;
        if (eventType === "moving" || eventType === "entry") {
            if (movingCarState.hasOwnProperty(car['id'])) {
                if (new Date(eventTimestamp) >= movingCarState[car['id']]['timestamp']) {
                    movingCarState[car['id']] = { timestamp: new Date(eventTimestamp), object: car }
                }
            } else {
                movingCarState[car['id']] = { timestamp: new Date(eventTimestamp), object: car }
            }
        }
        else if (eventType === "exit") {
            if (movingCarState.hasOwnProperty(car['id'])) {
                delete movingCarState[car['id']]
            }
        }
    }
}

/** The cars in the aisle which haven't moved for certain amount of time are retired
 * using this function.
 */
function retireCars(movingCarDict, movingCarState,currentTimestamp) {
    for (const key of Object.keys(movingCarState)) {
        let lastMovingTimestampOfCar = movingCarState[key]['timestamp'];
        if (currentTimestamp - lastMovingTimestampOfCar >= config.garage.backend.carRemovalPeriodInMs) {
            let car = movingCarState[key]['object'];
            car['removed'] = 1;
            movingCarDict[car['id']] = { timestamp: currentTimestamp, object: car }
            delete movingCarState[key]
        }
    }
}

/** Aggregates the parking spot and aisle related results into a single list after post processing */
function getResultList(parkingSpotResults,movingCarDict) {
    let resultList=parkingSpotResults;
    for (const key of Object.keys(movingCarDict)) {
        if (movingCarDict.hasOwnProperty(key)) {
            resultList.push(movingCarDict[key]["object"]);
        }
    }
    return (resultList);
}

/** Car objects in the list are sorted on the basis of event timestamp */
function sortByEventTimestamp(resultList) {   
    resultList.sort(function (a, b) {
        return a.timestamp - b.timestamp;
    });
    return (resultList);
}

/** Used to send the processed message to web socket client at regular intervals of time */
function sendMessage(ws, startTimestamp, currentTimestamp, previousTimestamp, isDeltaParkingSpotQuery, garageId, garageLevel,movingCarState) {
    return new Promise(function (resolve, reject) {
        var results = {
            timestamp: currentTimestamp.toISOString(),
            cars: new Array(),
            markers: new Array()
        }
        getResults(isDeltaParkingSpotQuery, garageId, garageLevel, previousTimestamp, currentTimestamp, startTimestamp).then(result => {
            let parkingSpotResults = result.parkingSpotResults
            let movingResults = result.movingResults
            var movingCarDict = getMovingCarDict(movingResults);
            updateMovingCarState(movingResults,movingCarState);
            retireCars(movingCarDict,movingCarState,currentTimestamp);
            let resultList=getResultList(parkingSpotResults,movingCarDict);       
            let sortedCars = sortByEventTimestamp(resultList);

            results["cars"] = sortedCars;

            var msgToDisplay = JSON.stringify(results)
            if (msgToDisplay.length > 30) {
                msgToDisplay = msgToDisplay.substring(0, 26) + " ..."
            }
            logger.info("Sending msg: %s: %s ", currentTimestamp, msgToDisplay);
            var msgToSend = JSON.stringify({ metadata: { timestamp: currentTimestamp.toISOString(), garageLevel: garageLevel }, data: results });
            ws.send(msgToSend, function ack(error) {
                if (error) {
                    //logger.info("[SEND UPDATES] Unable to send message: %s: %s . Closing connection", currentTimestamp, msgToDisplay)
                    reject({ error: error, msgToDisplay: msgToDisplay });
                }
                resolve({ error: null, msgToDisplay: msgToDisplay });
            });
        }).catch(error => {
            // logger.info("[SEND UPDATES] Unable to send message: %s: %s . Closing connection", currentTimestamp, msgToDisplay)
            reject({ error: error, msgToDisplay: null });
        });
    });
}

module.exports = {
    /** Initializes the set of spots. This is done when the server starts and reads the parking spot config file. */
    init: function (spots) {
        spotSet =spots
    },
    /** Uses the startTimestamp, garageId and garageLevel sent by websocket client to send results to the client at regular intervals of time */
    sendUpdates: function (ws, startTimestamp, garageId, garageLevel) {
        try {
            var timestampInMs = Date.parse(startTimestamp)
            if (isNaN(timestampInMs) == false) {
                startTimestamp = new Date(startTimestamp);
                let timeDifference= new Date()-startTimestamp;
                let currentTimestamp=new Date(new Date()-timeDifference);
                let previousTimestamp=new Date(startTimestamp-CLI_SEND_PERIOD_IN_MS);
                var isDeltaParkingSpotQuery = false
                var movingCarState = {}
                var intObj = setInterval(function () {
                    sendMessage(ws, startTimestamp, currentTimestamp, previousTimestamp, isDeltaParkingSpotQuery, garageId, garageLevel,movingCarState).then(result => {
                        isDeltaParkingSpotQuery = true
                        previousTimestamp=new Date(currentTimestamp.toISOString());
                        currentTimestamp=new Date(new Date()-timeDifference);
                    }).catch(errorObject => {
                        console.error(errorObject.error)
                        logger.info("[SEND UPDATES] Unable to send message: %s: %s . Closing connection", currentTimestamp, errorObject.msgToDisplay)
                        clearInterval(intObj);
                    });
                }, CLI_SEND_PERIOD_IN_MS);
                return intObj;
            } else {
                logger.error('[SERVER ERROR] Invalid Timestamp');
                ws.send(JSON.stringify({ error: " Invalid Timestamp" }), function ack(err) {
                    if (err) {
                        logger.info("[SEND UPDATES] Unable to send error message to client that error has occurred: %s . Closing connection", JSON.stringify({ error: err }))
                    }
                });
            }
        } catch (e) {
            logger.error('[SERVER ERROR] Error: %s', e);
            ws.send(JSON.stringify({ error: e.toString() }), function ack(err) {
                if (err) {
                    logger.info("[SEND UPDATES] Unable to send error message to client that error has occurred: %s . Closing connection", JSON.stringify({ error: err }))
                }
            });
        }
    }
}