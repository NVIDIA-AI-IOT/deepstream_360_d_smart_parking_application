import React, { Component } from 'react';
import moment from 'moment';

import classes from './HomeMap.css';

import Map from '../Component/Map/Map';
import SmartGaragePage from './SmartGaragePage/SmartGaragePage';
import Header from '../Component/Header/Header';
import Footer from '../Component/Footer/Footer';

/**
 * HomeMap.js renders all garage pages and Map.js which contains Google Maps component. 
 * The selected garage will be rendered and its state will be lifted up to HomeMap.js 
 * and then passed down to Map.js. By one click on the location marker, 
 * HomaMap.js zooms in the map to the particular garage.
 *
 * HomeMap.js also handles actions/events executed by the users, i.e. playing videos, 
 * clicking on license plate for information dialog box, and switching the page between 
 * all garages or different garage’s levels.
 * 
 * To add more garage locations, the garage page component, e.g. SmartGaragePage.js, 
 * should be imported here.
 */
class HomeMap extends Component {
    state = {
        googlemap: this.props.locations.home.googleMap,
        groundoverlay: null,
        cameras: [],
        video: {},
        plate: '',
        zoom: 14,
        centerWithin: {
            garage: false,
        },
        bounds: {
            garage: this.props.locations.garage.bounds,
        },
        garageLevel: '',
        websocket: {
            url: ''
        },
        user: {
            name: '',
            type: ''
        },
    }

    /* retrieve information from location */
    getMapInfo = (googlemap, groundoverlay, websocket, cameras) => {
        this.setState({
            googlemap: googlemap,
            groundoverlay: groundoverlay,
            websocket: websocket,
            cameras: cameras
        });
    }

    /* lift up video state */
    videoClickHandler = (video) => {
        console.log(video);
        this.setState({ video: video });
    }

    /* lift up license plate */
    plateClickHandler = (plate) => {
        this.setState({ plate: plate });
    }

    clearPlateHandler = () => {
        this.setState({ plate: '' });
    }

    /* lift up zoom size */
    getZoomHandler = (zoom) => {
        this.setState({ zoom: zoom });
    }

    isCenterWithinBounds = (name, bool) => {
        let centerWithin = Object.assign({}, this.state.centerWithin);
        centerWithin[name] = bool;
        this.setState({ centerWithin: centerWithin });
    }

    /* change the garage level */
    onSmartGarageLevelSelect = (level) => {
        this.setState({ garageLevel: level });
    }

    componentWillReceiveProps(nextProps) {
        /* user clicked location marker other than current/previous one */
        if (this.props.path !== nextProps.path) {
            if (nextProps.zoom !== null && nextProps.zoom !== undefined && nextProps.centerWithin !== null && nextProps.centerWithin !== undefined) {
                this.setState({
                    zoom: nextProps.zoom,
                    centerWithin: {
                        [nextProps.centerWithin.name]: nextProps.centerWithin.bool
                    }
                });
            }
        }
    }

    componentDidMount() {
        if (this.props.zoom !== null && this.props.zoom !== undefined && this.props.centerWithin !== null && this.props.centerWithin !== undefined) {
            this.setState({
                zoom: this.props.zoom,
                centerWithin: {
                    [this.props.centerWithin.name]: this.props.centerWithin.bool
                }
            });
        }
    }

    shouldComponentUpdate(nextState, nextProps) {
        return nextState.garageLevel !== this.state.garageLevel;
    }

    render() {
        
        let showContent, mapStyle, googlemap = this.state.googlemap, groundoverlay = null, websocket = {}, cameras = [];
        
        let startTimestamp = this.props.locations.garage.isLive ? this.props.locations.garage.live.apis.startTimestamp : this.props.locations.garage.playback.apis.startTimestamp;
        let diffTime = this.props.locations.garage.isLive ? '' :  moment.utc().diff(moment.utc(startTimestamp), 's');
       
        if (this.state.zoom > 16) {

            /* show the garage layer only if the zoom size is larger than 16 */
            if (this.state.centerWithin.garage) {
                window.location.hash = '#/garage';
                showContent = <SmartGaragePage
                    user={this.state.user}
                    getMapInfo={this.getMapInfo}
                    videoClickHandler={this.videoClickHandler}
                    plateClickHandler={this.plateClickHandler}
                    video={this.state.video}
                    isCenterWithinBounds={this.isCenterWithinBounds}
                    zoom={this.state.zoom}
                    centerWithin={this.state.centerWithin.garage}
                    levelSelect={this.onSmartGarageLevelSelect}
                    location={this.props.locations.garage}
                    diffTime={diffTime}
                />;
                googlemap = this.state.googlemap;
                groundoverlay = this.state.groundoverlay;
                websocket = this.state.websocket;
                cameras = this.state.cameras;
            }
        }

        if (showContent !== null && showContent !== undefined) {
            mapStyle = window.innerWidth < 900 ? {
                height: 'calc(100vh - 117px)'
            } : {
                    height: 'calc(100vh - 132px)'
                };
        }

        return (
            <div>
                <Header />
                <div className={classes.container}>
                    {/* show garage layer */}
                    {showContent}
                    <div className={classes.bodycontainer}>
                        <div className={classes.mapcontainer} style={mapStyle}>
                            {/* show google map layer and markers on the map */}
                            <Map
                                plate={this.state.plate}
                                clearPlate={this.clearPlateHandler}
                                click={this.videoClickHandler}
                                googlemap={googlemap}
                                groundoverlay={groundoverlay}
                                websocket={websocket}
                                cameras={cameras}
                                locations={this.props.locations.home.locations}
                                getZoomHandler={this.getZoomHandler}
                                isCenterWithinBounds={this.isCenterWithinBounds}
                                bounds={this.state.bounds}
                                zoom={this.state.zoom}
                                garageLevel={this.state.garageLevel}
                                location={this.props.locations.garage}
                            />
                        </div>
                    </div>
                </div>
                <Footer user={this.state.user.name} />
            </div>
        )
    }
}

export default HomeMap;