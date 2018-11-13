'use strict';

// Loading required libraries and config file
const es = require('elasticsearch');
const uuidv4 = require('uuid/v4');
const config = require('../../config/config.json');
var winston = require('winston');
var deepcopy = require("deepcopy");
var logger = winston.createLogger({
    transports: [
        new (winston.transports.Console)({ 'timestamp': true, level: 'error' })
    ],
    exitOnError: false
});
// Connection to elasticsearch
const esClient = new es.Client({
    host: [
        {
            host: config.garage.backend.esHost,
            port: config.garage.backend.esPort
        }
    ]
});

/** Checks if index exists */
const checkIndexExists = (indexName) => {
    return new Promise(function (resolve, reject) {
        esClient.indices.exists({ index: indexName }).then(response=> {
            resolve(response)
        }).catch(error=>{
            reject(error);
        });
    });
}

/** Queries the Event Index and returns the results */
const getEvents = (query,isSearch) => {
    return new Promise(function (resolve, reject) {
        let indexName = config.garage.backend.esEventsIndex;
        checkIndexExists(indexName).then(indexExist=>{
            if(indexExist){
                let queryObject={
                    index: indexName,
                    q: query,
                    sort: '@timestamp:desc',
                    _sourceInclude: [
                        'object.vehicle.license', '@timestamp',
                        'place.entrance.level','place.parkingSpot.level', 'place.aisle.level',
                        'event.type',
                        'videoPath'
                    ]
                };
                if(isSearch){
                    queryObject['size']=config.garage.backend.anomalyEventQuerySize;
                }else{
                    queryObject['size']=config.garage.backend.eventApiQueryResultSize;
                }
                esClient.search(queryObject).then(results => {
                    results = results.hits.hits;
                    resolve(results);
                }).catch(error => {
                    reject(error)
                });
            }else{
                resolve([]);
                logger.info('[ALERT!] Index not yet created');
            }
        }).catch(error => {
            reject(error)
        });
    });
}

/** Queries the Anomaly Index and returns the results */
const getAnomaly = (query) => {
    return new Promise(function (resolve, reject) {
        let indexName = config.garage.backend.esAnomalyIndex;
        checkIndexExists(indexName).then(indexExist=>{
            if(indexExist){
                esClient.search({
                    index: indexName,
                    size: config.garage.backend.anomalyEventQuerySize,
                    q: query,
                    sort: '@timestamp:desc',
                    _sourceInclude: [
                        'object.vehicle.license', '@timestamp',
                        'place.entrance.level', 'place.parkingSpot.level', 'place.aisle.level',
                        'analyticsModule.description',
                        'entryVideo', 'exitVideo', 'endTimestamp'
                    ]
                }).then(results => {
                    results = results.hits.hits;
                    resolve(results);
                }).catch(error => {
                    reject(error)
                });
            }else{
                resolve([]);
                logger.info('[ALERT!] Index not yet created');
            }
        }).catch(error => {
            reject(error)
        });
    });
}

/** Queries the Event Index and returns the results */
const getEventsDeprecated = (query) => {
    return new Promise(function (resolve, reject) {
        let indexName = config.garage.backend.esEventsIndex;
        checkIndexExists(indexName).then(indexExist=>{
            if(indexExist){
                esClient.search({
                    index: indexName,
                    size: config.garage.backend.anomalyEventQuerySize,
                    q: query,
                    sort: '@timestamp:desc',
                    _sourceInclude: [
                        'object.vehicle.license', '@timestamp',
                        'place.entrance.level','place.parkingSpot.level', 'place.aisle.level',
                        'event.type',
                        'videoPath'
                    ]
                }).then(results => {
                    results = results.hits.hits;
                    resolve(results);
                }).catch(error => {
                    reject(error)
                });
            }else{
                resolve([]);
                logger.info('[ALERT!] Index not yet created');
            }
        }).catch(error => {
            reject(error)
        });    
    });
}


/** Used to obtain the start and end index of search tokens in a complex search query string */
function getTokenAttributes(token,tokenAttributes){
    let newTokenAttributes=deepcopy(tokenAttributes);
    let extractedToken=token.substring(tokenAttributes.start,tokenAttributes.end)
    if (extractedToken.startsWith('(')||extractedToken.startsWith('!')){
        newTokenAttributes.start+=1;
    }else if(extractedToken.endsWith(')')){
        newTokenAttributes.end-=1;
    }
    if(tokenAttributes.start===newTokenAttributes.start && tokenAttributes.end===newTokenAttributes.end){
        return tokenAttributes;
    }else{
        return getTokenAttributes(token,newTokenAttributes);
    }
}

/** Formats the search query */
function formatSearchQuery(q,timeQuery){
    if(q==null){
        return(timeQuery);
    }
    let luceneOperatorSet=new Set(["||","&&","!","OR","AND","NOT"]);
    let tokenList=q.split(" ");
    for(let i=0;i<tokenList.length;i++){
        let token=tokenList[i];
        if(!luceneOperatorSet.has(token)){
            tokenList[i]=token;
            let tokenAttributes={start:0,end:token.length};
            tokenAttributes=getTokenAttributes(token,tokenAttributes);
            let finalExtractedToken=token.substring(tokenAttributes.start,tokenAttributes.end);
            tokenList[i]=token.substring(0,tokenAttributes.start)+'"'+finalExtractedToken+'"'+token.substring(tokenAttributes.end);
        }    
    }
    let formattedQuery=tokenList.join(" ");
    q='('+formattedQuery+') AND '+timeQuery;
    return q;
}

/**  The result is compressed so that a variety of events can be obtained for various detected objects. 
 * Moving events for a particular license plate is compressed based on the value mentioned for eventCompressionSize key in the config file.  
*/
function getCompressedResult(results){
    let compressedResult=new Array();
    let resultDictionary={};
    for (let result of results){
        if(result._source.event.type!=="moving"){
            compressedResult.push(result);
        }else{
            let key = result._source.object.vehicle.license === "" ? uuidv4() : result._source.object.vehicle.license;
            if (resultDictionary.hasOwnProperty(key.toString())) {
                resultDictionary[key].push(result);
            }else{
                resultDictionary[key]=new Array();
                resultDictionary[key].push(result);
            }
        }
    }
    let keys=Object.getOwnPropertyNames(resultDictionary);
    for(let key of keys){
        let resultList=resultDictionary[key];
        resultList.sort(function(x, y){
            return y._source['@timestamp'] - x._source['@timestamp'];
        });
        let slicedResultList=resultList.slice(0,config.garage.backend.eventCompressionSize);
        for (let result of slicedResultList) {
            compressedResult.push(result);
        }
    }
    compressedResult.sort(function(x, y){
        return y._source['@timestamp'] - x._source['@timestamp'];
    });
    return compressedResult;
}

module.exports={
    /** Formats the query before getting the events from elasticsearch and compresses the result before sending to client*/
    searchEvents:function(req,res,next){
        let q=req.query['q'];
        let timeQuery=req.query['timeQuery'];
        let isSearch=(req.query['isSearch']=== 'true');
        q=formatSearchQuery(q,timeQuery);
        getEvents(q,isSearch).then((response) => {
            if(isSearch){
                res.send(response);
            }else{
                let compressedResult=getCompressedResult(response);
                res.send(compressedResult.slice(0,config.garage.backend.anomalyEventQuerySize));
            }
        }).catch(error=>{
            console.log(error)
        });
    },
    /** Formats the query and gets the anomalies from elasticsearch */
    searchAnomaly:function(req,res,next){
        let q=req.query['q'];
        let timeQuery=req.query['timeQuery'];
        q=formatSearchQuery(q,timeQuery);
        getAnomaly(q).then((response) => {
            res.send(response);
        }).catch(error=>{
            console.log(error)
        });
    },
    /** Formats the query and gets the events from elasticsearch (Deprecated)*/
    searchEventsDeprecated:function(req,res,next){
        let q=req.query['q'];
        let timeQuery=req.query['timeQuery'];
        q=formatSearchQuery(q,timeQuery);
        getEventsDeprecated(q).then((response) => {
            res.send(response);
        }).catch(error=>{
            console.log(error)
        });
    }
}


