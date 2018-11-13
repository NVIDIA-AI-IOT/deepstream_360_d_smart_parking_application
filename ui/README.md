# UI

## Introduction

The UI for smart parking application is built using React.js and is used to visualize the state of a garage along with events and anomalies occurring in the garage. This UI can run in two modes: live and playback. The live mode is aimed for monitoring the garage in real time and the playback mode is used for demo purpose i.e. it is used to visualize pre-recorded data.

### UI Components

The component hierarchy of the UI is shown in the following diagram:

![Components](readme-images/Component-Hierarchy.jpeg?raw=true "Components")

**Component Description**

1. **App:**  App.js requests the config from Api and passes it down as props. It also navigates to another route for home/garage page.
2. **Home page:** HomeMap.js renders all garage markers and Map.js which contains Google Map component. The selected garage will then be rendered and its state will be lifted up to HomeMap.js and then passed down to Map.js. By clicking the location marker, HomeMap.js zooms in the map to the particular garage. It also handles actions/events executed by the users, i.e. playing videos, clicking on license plate for information dialog box, and switching the page between different garages or garage levels.
3. **Garage page:** SmartGaragePage.js is the main page of the garage. It consists consists of five main components: 
    + List window: Displays events/anomalies of detected cars
    + KPI information of Garage: Displays the current state of parking spots and also the entry/exit flowrate
    + Ground Overlay of Garage
    + Header and Footer
    + Search bar
4. **Map:** Map.js contains three main components: 
    + GoogleMap: It acts as a background for garage overlay
    + GroundOverlay: This is the overlay image of the garage
    + CarMarkers: These are the dots which are used to visualize parked and moving cars  
    **Note:** The center/bounds of the map changes at different zoom levels.
5. **Loader:** The loader for the browser can be customized by changing `Loader.css`
6. **Footer:** Footer.js contains four elements: 
    + Name of the application
    + Version of the application
    + User's information
    + Notes/Disclaimer
7. **Header:** Header.js contains five elements: 
    + Company's logo
    + Application name
    + Search bar with drop-down calendar
    + Question mark icon 
    + Hidden exclamation icon which appears when user selects invalid time bounds in search.
8. **Widget:** It is used to adjust the size of a panel which displays video or events/anomalies list to fit the screen size.
9. **List panel:** ListPanel.js displays the latest events/anomalies of a car. The number of messages displayed can be configured by changing the `alertEventListLength` parameter. By default, it refreshes every `alertEventRefreshIntervalSeconds` seconds by sending an Ajax query to obtain the latest events/anomalies of cars from the backend. The list panel will be updated with search results once the search query is triggered. If the search is without calendar, then the list panel refreshes the messages every `alertEventRefreshIntervalSeconds` seconds; if the user uses the calendar to search, then only the messages with tokens within the time bounds of search are shown.
10. **KPI:** Capacity.js sends an Ajax query to obtain the latest KPIs of the garage every `alertEventRefreshIntervalSeconds` seconds. KPIs includes available/occupied parking spots, and entry/exit flow.
11. **Search:** Search.js creates and lifts up the search query to SmartGaragePage.js. Each query includes search token, time bounds and hash location. If `isCalendar` is set to `true`, then time bounds are set using the calendar. If `isTimeValid` is set to `true`, then the selected time bounds are valid.
12. **Car marker:** CarMarkers.js under Map folder manages and updates each car marker, including its status and style of the marker.
13. **Overlay:** GroundOverlay.js under Map folder is a functional component which imports the garage's ground image and sets the bounds of the ground overlay.
14. **Garage marker:** LocationMarker.js under Map folder returns a clickable icon on Google Map which represents the garage's location. User can navigate to the garage page by clicking the marker. The marker's size will change at different zoom levels.
15. **Panel item:** Item.js within PanelItem folder is a functional component which returns key information retrieved from each message of a detected car.
16. **Marker worker:** MarkersWorker.js is located within public folder. It uses Web Workers to manage and update the status of cars which are sent through WebSocket.

The following illustration shows how the components are placed in the **Garage Page**
![Garage-Components](readme-images/Garage-Components.jpeg?raw=true "Garage-Components")

### Screenshots of the UI

The following image shows the home page with a garage marker. Although the image shows a single garage marker, the home page can contain multiple garage markers and user can navigate to any of the garage by just clicking the marker.
![Home-Page](readme-images/HomePage.PNG?raw=true "Home-Page")

Once the Garage Marker is clicked, the map 'zooms-in' to the location and renders the garage overlay along with other components.
![Garage](readme-images/Garage.PNG?raw=true "Garage")

## Getting Started

### Dependencies

Make sure you have a recent version of [Node.js](https://nodejs.org/en/ "Nodejs.org") installed on your local machine.
UI will also require Apis to be up and running. The Apis can be found [here](https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application/tree/master/apis). Follow the README instructions in the API repository to complete the setup. 

### Environment Variables

Export the following Environment variables if running UI outside dockers:
+ REACT_APP_BACKEND_IP_ADDRESS - The IP Address of the API server
+ REACT_APP_BACKEND_PORT - The port where the server is listening for requests
+ REACT_APP_GOOGLE_MAP_API_KEY - Google Map API key

Follow the instructions in this [link](https://developers.google.com/maps/documentation/javascript/get-api-key) to get an api key for Google Maps.

**Note:** Custom environment variables should begin with `REACT_APP_` otherwise they will be ignored except for `NODE_ENV`.

### Installation

Install `Node.js` and `Apis` as they are pre-requisites for this application.

Assuming that the application has been cloned from this repository

    git clone https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application.git
        
use the following command to change the current directory.

    cd ./ui

[package.json](package.json) has a list of libraries which are required for this application. Use `npm install` to install these dependencies of the project. 

Use `npm start` to run this application in development mode.

### Deployment

It is not a good idea to deploy UI in development mode in production machines. Before deploying to any web host, use `npm run-script build` to create an optimized build for production environment.
The build contains minified javascript files which can be found in the `build` directory. This build can be deployed to any web host using nginx by following the steps mentioned in this [link](https://medium.com/@timmykko/deploying-create-react-app-with-nginx-and-ubuntu-e6fe83c5e9e7). 

### Configuration

By maintaining a JSON configuration file in the backend, this app allows the users to customize their own garage. Below are the configurable features of this app:

**Homepage**

You can change the center of your map to your garage's location by editing the `lat` and `lng`.
```
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
```

**Garage Page**

```
"garage": {
        "name": "Garage",
        "defaults": {
            "level": "P1",
        },
```

Set bounds of the map for the garage. These bounds are the boundary of the map shown on the entry page. 
```
        "bounds": {
            "north": 37.2886489370708,
            "south": 37.2864695830171,
            "east": -121.983629765596,
            "west": -121.986218361030
        },
```

Customize the google map features on the background of the garage. 
```
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
```

GroundOverlay is the top-down perspective image of the garage. You can replace the image inside your `/src/asset` folder. The bounds of the image should be set properly to match the `lat` and `lng` of the garage on the google map. 
```
        "groundOverlay": {
            "p1GroundImage": "assets/X-StrpP1_simpleConverted.png",
            "p1Bounds": {
                "north": 37.2881998,
                "south": 37.2863798,
                "east": -121.9838699,
                "west": -121.9859025
            }
        },
```

`isLive` indicates the mode of the video source. If true, live video is used as the data source; otherwise, a pre-recorded video is used as the source.
```
        "isLive": false,
```

**Live vs Playback**

For both `live` and `playback`, `websocket` and `apis` are configurable. Websocket is used to update the car markers. For APIs, AJAX query is sent every `alertEventRefreshIntervalSeconds` secs (5 secs by default) to get events and anomalies data. `alertEventListLength` (20 items by default) is the max number of items shown on the list window. `dialogAutoCloseSeconds` (5 secs by default) is the pop-up time interval of the dialog box which shows parking information of each car and can be triggered by clicking on the car marker. 

The 3 settings that differentiate `live` and `playback` modes are as follows:
- `startTimestamp` is required only for the playback mode;
- `uiDelaySeconds` is required because the parking Spot data generated and sent by deepstream is usually delayed by a few seconds. By delaying the UI we show the accurate representation of the garage at that moment of time. 
- `autoRefreshIntervalMinutes` has to be set for the playback mode to send query in a time loop, and the length of the interval depends on the pre-recorded video's length.

```
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
        },
        "playback": {
            "webSocket": {
                "url": "",
                "startTimestamp": "2018-08-30T21:49:48.500Z",
                "garageId": "endeavor",
                "garageLevel": "P1",
                "dialogAutoCloseSeconds": 5
            },
            "apis": {
                "baseurl": "",
                "alerts": "/es/alerts",
                "events": "/es/events",
                "kpi": "/stats/endeavor",
                "startTimestamp": "2018-08-30T21:49:48.500Z",
                "alertEventRefreshIntervalSeconds": 5,
                "autoRefreshIntervalMinutes": 30,
                "uiDelaySeconds": 20,
                "alertEventListLength": 20
            }
        },
```
