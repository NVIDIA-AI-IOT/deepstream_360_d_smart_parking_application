'use strict';

// Loading required libraries and config file
var config = require('../../config/config.json');
var deepcopy = require("deepcopy");
const cassandra = require('cassandra-driver');
const cassandraHosts = config.garage.backend.cassandraHosts;

// Connection to Cassandra
const client = new cassandra.Client({ contactPoints: cassandraHosts, keyspace: config.garage.backend.cassandraKeyspace });
var availabilityDict;

/** A generic function which receives a queryObject and uses it to obtain results from cassandra. The queryObject consists of the query and the params. */
function getResultsFromCassandra(queryObject) {
    return new Promise(function (resolve, reject) {
        client.execute(queryObject['query'], queryObject['params'], { prepare: true })
            .then(result => {
                resolve(result.rows);
            }).catch(error => {
                reject(error);
            });
    });
}

/** Queries and provides the result for entry and exit flowrate */
function getFlowRate(garageId, timestampRange) {
    return new Promise(function (resolve, reject) {
        let isLive = config.garage.isLive;
        let queryObject = {}
        if (isLive && config.garage.live.apis.uiDelaySeconds===0) {
            queryObject['query'] = 'SELECT * FROM flowrate where id = :garageId  limit 1';
            queryObject['params'] = [garageId];
        }
        else if (isLive && config.garage.live.apis.uiDelaySeconds!==0) {
            queryObject['query'] = 'SELECT * FROM flowrate where id = :garageId and timestamp < :ts limit 1';
            queryObject['params'] = [garageId, timestampRange.toTs]
        }else if(!isLive){
            queryObject['query'] = 'SELECT * FROM flowrate where id = :garageId and timestamp >= :fromTs and timestamp < :toTs limit 1';
            queryObject['params'] = [garageId, timestampRange.fromTs, timestampRange.toTs]
        }
        getResultsFromCassandra(queryObject).then(results => {
            let x = null;
            if (results.length == 0) {
                x = { exit: null, entry: null }
            } else {
                x = results[0];
            }
            var exit = '0/hr'
            if (x.exit != null) {
                exit = ''.concat(x.exit, '/hr')
            }
            var entry = '0/hr';
            if (x.entry != null) {
                entry = ''.concat(x.entry, '/hr')
            }
            resolve({ "entry": entry, "exit": exit });
        }, error => {
            reject(error);
        });
    });
}

/** A sanity checker to validate the total occupied and available spots */
function statsValidator(parkingStats) {
    if (parkingStats.totalOccupied > availabilityDict.total) {
        parkingStats.totalOccupied = deepcopy(availabilityDict.total)
    }
    if (parkingStats.totalAvailable < 0) {
        parkingStats.totalAvailable = 0
    }
    return parkingStats;
}

/** Generates cassandra query for live system */
function getParkingSpotStateQuery(garageId, garageLevel) {
    let queryObject = {}
    queryObject["query"] = "select event,place from parkingSpotState where garageid= :garageId and level= :garageLevel";
    queryObject["params"] = [garageId, garageLevel];
    return (queryObject);
}

/** Generates cassandra query for playback system */
function getParkingSpotPlaybackQuery(garageId, garageLevel, timestampRange) {
    let parkingQueriesList = [];
    let sensorType=config.garage.backend.sensorType;
    let spotSet=availabilityDict.spotSet;
    let isLive = config.garage.isLive;
    for (let spot of spotSet) {
        let parkingSpotQueryObject = {}
        if (isLive && config.garage.live.apis.uiDelaySeconds!==0) {
            parkingSpotQueryObject['query'] = "select timestamp, spotid, place, sensor, object, event from parkingSpotPlayback where garageid=:garageId and level=:garageLevel and sensortype=:sensorType and spotid=:spotId and timestamp <= :ts limit 1";
            parkingSpotQueryObject['params'] = [garageId, garageLevel, sensorType, spot, timestampRange.toTs];
        }else if(!isLive){
            parkingSpotQueryObject['query'] = "select timestamp, spotid, place, sensor, object, event from parkingSpotPlayback where garageid=:garageId and level=:garageLevel and sensortype=:sensorType and spotid=:spotId and timestamp >= :fromTs and timestamp <= :toTs limit 1";
            parkingSpotQueryObject['params'] = [garageId, garageLevel, sensorType, spot, timestampRange.fromTs, timestampRange.toTs];
        }
        parkingQueriesList.push(parkingSpotQueryObject);
    }
    return(parkingQueriesList);
}

/** Resolves the queries generated for live and playback mode */
function getParkingResults(garageId, garageLevel, timestampRange) {
    return new Promise(function (resolve, reject) {
        let isLive = config.garage.isLive;
        if (isLive && config.garage.live.apis.uiDelaySeconds===0) {
            let queryObject = getParkingSpotStateQuery(garageId, garageLevel);
            getResultsFromCassandra(queryObject).then(results => {
                resolve(results);
            }).catch(error => {
                reject(error);
            });
        } else {
            let queryList=getParkingSpotPlaybackQuery(garageId, garageLevel, timestampRange);
            let playbackQueryList=queryList.map(getResultsFromCassandra);
            Promise.all(playbackQueryList).then(playbackResultList=>{
                let playbackResults=[].concat(...playbackResultList);
                resolve(playbackResults);
            }).catch(error=>{
                reject(error);
            });
        }
    });
}

/** Calculates the number of occupied and available spots based on the parked events*/
function getParkingStats(garageId, timestampRange) {
    return new Promise(function (resolve, reject) {
        const garageLevel = config.garage.backend.garageLevel;
        getParkingResults(garageId, garageLevel, timestampRange).then(parkingResults => {
            let parkingStats = {
                id: garageId,
                totalAvailable: deepcopy(availabilityDict.total),
                totalOccupied: 0
            };
            for (let i = 0; i < parkingResults.length; i++) {
                let row = parkingResults[i];
                if (row['event']['type'] === "parked") {
                    parkingStats.totalOccupied += 1;
                    parkingStats.totalAvailable -= 1;
                }
            }
            parkingStats = statsValidator(parkingStats);
            resolve(parkingStats);
        }).catch(error => {
            reject(error);
        });
    });
}

/** Returns the formatted timestamp Range */
function getFormattedTimestampRange(timeQuery) {
    var fromTs=timeQuery.slice(timeQuery.indexOf('[')+1,timeQuery.indexOf(' TO'));
    var toTs = timeQuery.slice(timeQuery.indexOf('TO') + 3, timeQuery.length - 1);
    return ({"fromTs":fromTs,"toTs":toTs});
}

module.exports = {
    /** Initializes the total available spots and the set of spots. This is done when the server starts and reads the parking spot config file. */
    init: function (availabilityDetails) {
        availabilityDict = {
            total: availabilityDetails.Total,
            spotSet: availabilityDetails.spotSet
        }
    },
    /** Reads garageId which is sent as a request parameter, gets the result of flowrate and parkingStats and sends the result in the form of a json object. */
    getStats: function (req, res, next) {
        var garageId = "unknown"
        if ("garageId" in req.params) {
            garageId = req.params.garageId
        }

        let timeQuery=req.query['timeQuery'];
        let formattedTimestampRange = getFormattedTimestampRange(timeQuery);

        Promise.all([getParkingStats(garageId, formattedTimestampRange),
        getFlowRate(garageId, formattedTimestampRange)]
        ).then(results => {
            let parkingStats = results[0];
            let flowRateResult = results[1];
            res.json({
                "id": parkingStats.id,
                "Free Spots": parkingStats.totalAvailable,
                "Occupied Spots": parkingStats.totalOccupied,
                "Entry Flow Rate": flowRateResult.entry,
                "Exit Flow Rate": flowRateResult.exit
            });
        }).catch(error => {
            console.log(error);
        });
    }
}