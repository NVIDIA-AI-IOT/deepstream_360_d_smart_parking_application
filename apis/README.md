# APIs
Exposes APIs and Websocket for smart parking application

## Introduction
This module which was built using Node.js provides apis which gives us the state of the garage and also the events and anomalies that are occurring in garage.
The events and anomalies api endpoints can also be used for searching. 
The events and anomalies are retrieved from elasticsearch whereas the state/KPI of the garage is retrieved from cassandra.
The apis are not just limited to stats of garage, an endpoint is also provided which supplies the configuration details to UI.
A websocket is also provided which reads cassandra to give live updates of the garage.

## Getting Started

### Dependencies

Make sure you have a recent version of [Node.js](https://nodejs.org/en/ "Nodejs.org") installed on your local machine.

It also requires `elasticsearch` and `cassandra` databases.

### Environment Variables

Export the following Environment variables if running Apis outside dockers:
+ **IP_ADDRESS** : IP Address of the host machine. If running locally, set it to localhost.
+ **NODE_PORT** : The port where server should be listening for requests.

### Installation

Install `Node.js`, `cassandra`, `elasticsearch` as they are pre-requisites for this application.

Assuming that the application has been cloned from this repository

    git clone https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application.git
        
use the following command to change the current directory.

    cd ./apis
    
[package.json](package.json) has a list of libraries which are required for this application. Use `npm install` to install these dependencies of the project. 

Use `npm start` to start the server.

## APIs exposed

### Config Related Apis
1. **UI config**
    + **Route**: /ui-config
    + **Params**: N/A
    + **Description**: This api is used to send config to UI which helps it render the markers for garage and also the details for other apis and websocket.
    + **Response**: If the system is live

            {
                "home": {
                    "name": "Home",
                    "username_api": "",
                    "googleMap": {
                        "defaultCenter": {
                            "lat": 37.2667081,
                            "lng": -121.9852038
                        },
                        "defaultZoom": 14,
                        "maxZoom": 21,
                        "minZoom": 10,
                        "mapTypeControl": true,
                        "mapTypeId": "roadmap"
                    },
                    "locations": [
                        {
                            "name": "garage",
                            "lat": 37.287535,
                            "lng": -121.98473
                        }
                    ]
                },
                "garage": {
                    "name": "Garage",
                    "defaults": {
                        "level": "P1"
                    },
                    "bounds": {
                        "north": 37.2886489370708,
                        "south": 37.2864695830171,
                        "east": -121.983629765596,
                        "west": -121.986218361030
                    },
                    "googleMap": {
                        "defaultCenter": {
                            "lat": 37.287535,
                            "lng": -121.98473
                        },
                        "defaultZoom": 19,
                        "maxZoom": 21,
                        "minZoom": 10,
                        "mapTypeControl": true,
                        "mapTypeId": "roadmap"
                    },
                    "groundOverlay": {
                        "p1GroundImage": "assets/X-StrpP1_simpleConverted.png",
                        "p1Bounds": {
                            "north": 37.2881998,
                            "south": 37.2863798,
                            "east": -121.9838699,
                            "west": -121.9859025
                        }
                    },
                    "isLive": true,
                    "live": {
                        "webSocket": {
                            "url": "",
                            "startTimestamp": "",
                            "garageId": "endeavor",
                            "garageLevel": "P1",
                            "dialogAutoCloseSeconds": 5
                        },
                        "apis": {
                            "baseurl": "",
                            "alerts": "/es/alerts",
                            "events": "/es/events",
                            "kpi": "/stats/endeavor",
                            "startTimestamp": "",
                            "alertEventRefreshIntervalSeconds": 5,
                            "uiDelaySeconds": 30,
                            "alertEventListLength": 20
                        }
                    }
                }
            }
   
        If its a playback system then `isLive` is set to `false` and the `playback` attribute of the config is sent instead of the `live` attribute.

### Garage related Apis
1. **Stats**
    + **Route**: /stats/:garageId
    + **Params**: q (Contains a timestamp range for the stats query)
    + **Description**: This api gets the parking spot stats of the garageId given as part of the url and also the flowrate of the garage.
    + **Response**: 
            
            {
                "id": <Id of garage>,
                "Free Spots": <Number of available spots>,
                "Occupied Spots": <Number of occupied spots>,
                "Entry Flow Rate": <Entry flowrate of garage>,
                "Exit Flow Rate": <Exit flowrate of garage>
            }
            
2. **Alerts**<br/>
    + **Route**: /es/alerts
    + **Params**: q (Contains a timestamp range for the alerts query. It may also contain search tokens)
    + **Description**: This api is used to list all the anomalies in garage.
    + **Response**: The response contains the result object from elasticsearch. This contains the attributes of the car object performing anomalous behavior.
3. **Events**
    + **Route**: /es/events
    + **Params**: q (Contains a timestamp range for the events query. It may also contain search tokens)
    + **Description**: This api is used to list all the events in garage. The api compresses the results so that multiple types of events can be displayed during a time interval, rather than just viewing the moving event of a single car object.
    + **Response**: The response contains the result object from elasticsearch. This contains the attributes of the car object whose events are being detected.
4. **Events-Deprecated**
    + **Route**: /es/events-deprecated
    + **Params**: q (Contains a timestamp range for the events query. It may also contain search tokens)
    + **Description**: This api is used to list all the events in garage. It has been deprecated as compression of events doesn't happen in this version of the api.
    + **Response**: The response contains the result object from elasticsearch. This contains the attributes of the car object whose events are being detected.


## Websocket exposed
1. **Live update of Garage**
   + **Route**: /
   + **Initial Message**: Initial message sent by client should be in json format with the following attributes
        
            {   
                "garageId": <Id of Garage>, 
                "garageLevel": <Level of Garage>, 
                "startTimestamp": <The startTimestamp of the websocket. It should be in the following format: YYYY-MM-DDTHH:MM:SS.fffZ>
            }
   + **Description**: The websocket provides parking spot and aisle related updates to the client.
   + **Response**: An array of car objects. A sample car object has the following attributes
   
            {
                "timestamp": <Timestamp of Event>,
                "color": <Color of Object>,
                "garageLevel": <Level of garage>,
                "id": <Id of object>,
                "licensePlate": <License Plate>,
                "licenseState": <License State>,
                "orientation": <Orientation of object>,
                "parkingSpot": <Parking Spot Id. It will be null for moving cars.>,
                "sensorType": <Type of sensor>,
                "state": <State of the car. Possible values are moving,parked,empty>,
                "eventType": <Type of event>,
                "removed": <A flag which indicates if the car needs to be removed/retired from UI>,
                "type": <Type of vehicle>,
                "x": <X coordinate of object>,
                "y": <Y coordinate of object>,
                "lat": <Latitude of object>,
                "lon": <Longitude of object>
            }
    
    
## Configuration File

The `config.json` file is present inside the `config` directory. This file consolidates all the parameters being used by ui and backend into a single file.

The UI part of the config file has already been explained in the README of UI.

The attributes of backend configuration looks as follows:
    
    {
        "cassandraHosts": <An array of cassandra hosts>,
        "cassandraKeyspace": <Name of the cassandra keyspace being used>,
        "esHost": <Elasticsearch host>,
        "esPort": <Elasticsearch port>,
        "esAnomalyIndex": <Anomaly index in elasticsearch>,
        "esEventsIndex": <Events index in elasticsearch>,
        "eventCompressionSize":<Compression factor for moving events of a car>,
        "anomalyEventQuerySize":<Size of Anomaly, Events that will be returned by the alerts/events api>,
        "eventApiQueryResultSize":<Size of result that will be returned by the elasticsearch for events api>,
        "parkingSpotConfigFile": <Parking Spot config file which lists all the spots available in a garage>,
        "sensorType": <Type of sensor being used>,
        "garageLevel": <Level of the garage>,
        "webSocketSendPeriodInMs": <Interval in ms after which websocket should send messages>,
        "carRemovalPeriodInMs": <Interval in ms after which non-moving cars in aisle of garage should be retired>,
        "originLat": <Latitude of center of garage>,
        "originLon": <Longitude of center of garage>
    }
