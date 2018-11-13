import React, { Component } from 'react';

import CarMarker from './CarMarker/CarMarker';

const google = window.google;

/**
 * CarMarkers.js manages and updates each car marker, 
 * including its status and its marker’s style. 
 * All car markers are located one layer above the ground map.
 * 
 * Use WebSocket to receive and send messages to update the status, 
 * i.e. parked, empty, and moving of each car marker. 
 */
class CarMarkers extends Component {
    state = {
        cars: {}
    }

    componentDidMount() {
        /* if there is a websocket url. */
        if (this.props.websocket.url !== '' || this.props.websocket.url !== undefined) {
            /* if browser supports web worker. */
            if (window.Worker) {
                /* use web worker to finish websocket call and generate data. */
                this.myWorker = new Worker('/MarkersWorker.js');

                let socketRequest;
                socketRequest = JSON.stringify({
                    startTimestamp: this.props.websocket.startTimestamp,
                    garageLevel: this.props.websocket.garageLevel,
                    garageId: this.props.websocket.garageId
                });

                this.myWorker.postMessage([this.props.websocket.url, socketRequest, window.location.hash]);
                this.myWorker.onmessage = (m) => {
                    this.setState({ cars: m.data });
                }
            }
        }
    }

    shouldComponentUpdate(nextProps, nextState) {
        /* only update when zoom/garageLevel/bounds/markers (moving/add/remove) change */
        return this.props.zoom !== nextProps.zoom || this.props.websocket.garageLevel !== nextProps.websocket.garageLevel || !this.props.bounds.equals(nextProps.bounds) || this.state.cars !== nextState.cars;
    }

    componentDidUpdate(prevProps, prevState) {
        /* if there is a websocket url or zoom changed, and location changed */
        if ((this.props.websocket.url !== '' || this.props.websocket.url !== undefined || this.props.zoom !== prevProps.zoom) && this.props.websocket.garageLevel !== prevProps.websocket.garageLevel) {
            this.setState({
                cars: {}
            });

            let socketRequest;
            socketRequest = JSON.stringify({
                startTimestamp: this.props.websocket.startTimestamp,
                garageLevel: this.props.websocket.garageLevel,
                garageId: this.props.websocket.garageId
            });

            this.myWorker.postMessage([this.props.websocket.url, socketRequest, window.location.hash]);
            this.myWorker.onmessage = (m) => {
                this.setState({ cars: m.data });
            }
        }
    }

    componentWillUnmount() {
        this.myWorker.terminate();
    }

    render() {

        let carmarkers = [];
        let isOpen = false;
        Object.entries(this.state.cars).forEach(([key, value]) => {
            isOpen = value.state === 'moving';
            if (this.props.bounds.contains(new google.maps.LatLng(value.lat, value.lon))) {
                carmarkers.push(
                    <CarMarker
                        key={key}
                        car={value}
                        clearPlate={this.props.clearPlate}
                        isOpen={isOpen}
                        zoom={this.props.zoom}
                        config={this.props.config}
                    />
                );
            }
        });
        return carmarkers;
    }
}

export default CarMarkers;