import React, { Component } from 'react';
import { compose, withProps } from 'recompose';
import debounce from 'lodash.debounce';
import { withGoogleMap, GoogleMap } from 'react-google-maps';

//import CameraMarker from './CameraMarker/CameraMarker';
import CarMarkers from './CarMarkers/CarMarkers';
import GroundOverlay from './GroundOverlay/GroundOverlay';
import LocationMarker from './LocationMarker/LocationMarker';

const google = window.google;

/**
 * Map.js contains three main components: 
 * (1) GoogleMap which is the background map of garage’s overlay;
 * (2) groundOverlay which is garage’s overlay; 
 * (3) CarMarkers which locates occupied spots and moving cars. 
 * 
 * Users can configure the google map settings, 
 * i.e. zoom control, and the center/bounds of the map.
 * 
 * The center/bounds of the map will change at different zoom levels.
 */
class Map extends Component {
    state = {
        zoom: this.props.googlemap.defaultZoom,
        center: this.props.googlemap.defaultCenter,
        bounds: this.props.googlemap.bounds !== undefined ? new google.maps.LatLngBounds(
            new google.maps.LatLng(this.props.googlemap.bounds.south, this.props.googlemap.bounds.west),
            new google.maps.LatLng(this.props.googlemap.bounds.north, this.props.googlemap.bounds.east)
        ) : null
    }

    /* computer whether inbound after 10ms  of last map center changed -- for different garage locations */
    emitChangeDebounced = debounce((value) => {
        Object.getOwnPropertyNames(this.props.bounds).forEach((el) => {
            this.props.isCenterWithinBounds(el, new google.maps.LatLngBounds(
                new google.maps.LatLng(this.props.bounds[el].south, this.props.bounds[el].west),
                new google.maps.LatLng(this.props.bounds[el].north, this.props.bounds[el].east)
            ).contains(value));
        });
    }, 10);

    /* computer map bounds after 100ms of last map center changed -- for one location zoom-in render markers based on view bounds */
    emitBoundDebounce = debounce(() => {
        this.setState({ bounds: this.myMap.getBounds() });
    }, 100);

    /* get current map zoom */
    getZoomHandler = () => {
        this.setState({ zoom: this.myMap.getZoom(), bounds: this.myMap.getBounds() });
        this.props.getZoomHandler(this.myMap.getZoom());
    }

    /* get current map center */
    getCenterHandler = () => {
        this.emitBoundDebounce();
        this.emitChangeDebounced(this.myMap.getCenter().toJSON());
        this.setState({ center: this.myMap.getCenter().toJSON() });
    }

    componentWillReceiveProps(nextProps) {
        /* if user clicked location marker */
        if (this.props.googlemap.defaultCenter !== undefined && (this.props.googlemap.defaultCenter.lat !== nextProps.googlemap.defaultCenter.lat || this.props.googlemap.defaultCenter.lng !== nextProps.googlemap.defaultCenter.lng || (window.location.hash !== '#/home' && this.state.zoom !== nextProps.zoom))) {
            this.setState({
                zoom: nextProps.zoom,
                center: nextProps.googlemap.defaultCenter,
                bounds: nextProps.googlemap.bounds !== undefined ? new google.maps.LatLngBounds(
                    new google.maps.LatLng(nextProps.googlemap.bounds.south, nextProps.googlemap.bounds.west),
                    new google.maps.LatLng(nextProps.googlemap.bounds.north, nextProps.googlemap.bounds.east)
                ) : null
            });
        }
    } 

    componentWillUnmount() {
        this.emitChangeDebounced.cancel();
        this.emitBoundDebounce.cancel();
    }

    render() {
        let markers;
        /* if zoom > 16 && there are websocket url, show car&camera markers */
        if (this.state.zoom > 16 && this.props.websocket.url !== undefined && this.props.websocket.url !== null && this.props.websocket.url !== '') {
            markers = [
                <CarMarkers
                    key="carmarkers"
                    websocket={this.props.websocket}
                    plate={this.props.plate}
                    zoom={this.state.zoom}
                    clearPlate={this.props.clearPlate}
                    garageLevel={this.props.garageLevel}
                    bounds={this.state.bounds}
                    config={this.props.location}
                />,
                // *<CameraMarker
                //     zoom={this.state.zoom}
                //     click={this.props.click}
                //     cameras={this.props.cameras}
                //     key="cameramarker"
                // />
            ];
        }
        /* if zoom <= 16, show location markers */
        else if (this.state.zoom <= 16) {
            markers = <LocationMarker locations={this.props.locations} zoom={this.state.zoom} />;
        }

        let groundoverlay;
        /* if there is groundoverlay, show it */
        if (this.props.groundoverlay !== undefined && this.props.groundoverlay !== null) {
            groundoverlay = <GroundOverlay groundoverlay={this.props.groundoverlay} />
        }

        /* remove business and transit labels from map */
        return (
            <GoogleMap
                defaultOptions={{
                    maxZoom: this.props.googlemap.maxZoom,
                    minZoom: this.props.googlemap.minZoom,
                    styles: [
                        {
                            featureType: 'poi.business',
                            stylers: [{ visibility: 'off' }]
                        },
                        {
                            featureType: 'transit',
                            elementType: 'labels.icon',
                            stylers: [{ visibility: 'off' }]
                        }
                    ]
                }}
                mapTypeId={this.props.googlemap.mapTypeId}
                ref={(ref) => { this.myMap = ref; }}
                onZoomChanged={this.getZoomHandler}
                zoom={this.state.zoom}
                onCenterChanged={this.getCenterHandler}
                center={this.state.center}
            >
                {groundoverlay}
                {markers}
            </GoogleMap>
        );
    }
}

export default compose(
    withProps({
        loadingElement: <div style={{ height: `100%` }} />,
        containerElement: <div style={{ height: `100%` }} />,
        mapElement: <div style={{ height: `100%` }} />,
    }),
    withGoogleMap
)(Map);