import React, { Component } from 'react';
import { Marker, InfoWindow } from 'react-google-maps';
import Moment from 'moment';

import classes from './CarMarker.css';
import green from '../../../../assets/green.png';
import blue from '../../../../assets/blue.png';

/**
 * Add the information dialog box to each parked/moving car marker.
 * After click on the car marker, the dialog box will pop up and 
 * disappear after `dialogAutoRefreshIntervalSeconds` secs and it's 
 * 5 secs by default; 
 * 
 * Configure the color and the size of the marker. To change the
 * color of the markers, replace the image file `green.png` or `blue.png`
 * with a new file showing different colored circle image;
 * 
 * Configurable variable: `dialogAutoRefreshIntervalSeconds`
 */
class CarMarker extends Component {
    state = {
        isOpen: false,
        touched: false,
        dialogAutoRefreshIntervalSeconds: this.props.config.isLive ? this.props.config.live.webSocket.dialogAutoCloseSeconds : this.props.config.playback.webSocket.dialogAutoCloseSeconds
    }

    /* toggle to open/close info window */
    onToggleHandler = () => {
        this.setState({ isOpen: !this.state.isOpen, touched: true });
        if (this.props.clearPlate !== undefined) {
            this.props.clearPlate();
        }
        if (this.props.jump !== undefined) {
            this.props.jump(this.props.index);
            this.autoCloseHandler();
        }
    }

    /* close info window after x=dialogAutoRefreshIntervalSeconds seconds, 
     * and the default setting is 5 secs */
    autoCloseHandler = () => {
        this.timeout = setTimeout(() => {
            if (this.marker) {
                this.setState({ isOpen: false });
            }
        }, this.state.dialogAutoRefreshIntervalSeconds * 1000);
    }

    componentDidMount() {
        if (this.props.isOpen && this.props.car.state === 'moving') {
            this.setState({ isOpen: true });
        }
    }

    componentWillReceiveProps(newProps) {
        /* if props.isOpen true and this marker is not touched, open info window */
        if (newProps.isOpen && !this.state.touched) {
            this.setState({ isOpen: newProps.isOpen });
            /* this is not a moving car, start auto close timer */
            if (newProps.car.state !== 'moving') {
                this.autoCloseHandler();
            }
        }
        /* if props.isOpen false and marker is touched, set touched to false */
        else if (!newProps.isOpen && this.state.touched) {
            this.setState({ touched: false });
        }
        /* if car.state changes from moving to parked, start auto close timer */
        else if (!newProps.isOpen && this.state.isOpen && !this.state.touched && this.props.car.state === 'moving' && newProps.car.state === 'parked') {
            this.autoCloseHandler();
        }
    }

    shouldComponentUpdate(nextProps, nextState) {
        /* update component when car is moving and lat/lng changed, or isOpen changed, or map zoom changed */
        return (this.props.car.state === 'moving' && (this.props.car.lat !== nextProps.car.lat || this.props.car.lon !== nextProps.car.lon)) || this.state.isOpen !== nextState.isOpen || this.props.zoom !== nextProps.zoom;
    }

    componentDidUpdate() {
        if (this.props.car.state !== 'moving') {
            this.autoCloseHandler();
        }
    }

    componentWillUnmount() {
        clearTimeout(this.timeout);
    }

    render() {
        let icon, info;
        /* decide the size and the color of car icon shown on map */
        
        /* for parked car, show green dot */
        if (this.props.car !== undefined && this.props.car.state === "parked") {
            let parkingTime = Moment(this.props.car.timestamp).local().format('YYYY-MM-DD HH:mm:ss.SSS');
            /* add items to the dialog box */
            info = (
                <p>
                    License: {this.props.car.licensePlate}<br />
                    ParkingSpot: {this.props.car.parkingSpot}<br />
                    Sensor: {this.props.car.sensorType}<br />
                    Timestamp: {parkingTime}
                </p>
            );
            switch (this.props.zoom) {
                case 19:
                    icon = {
                        url: green,
                        scaledSize: { width: 8, height: 8 },
                        anchor: { x: 4, y: 4 }
                    };
                    break;
                case 20:
                    icon = {
                        url: green,
                        scaledSize: { width: 16, height: 16 },
                        anchor: { x: 8, y: 8 }
                    };
                    break;
                case 21:
                    icon = {
                        url: green,
                        scaledSize: { width: 26, height: 26 },
                        anchor: { x: 13, y: 13 }
                    };
                    break;
                default:
                    icon = {
                        url: green,
                        scaledSize: { width: 12, height: 12 },
                        anchor: { x: 6, y: 6 }
                    };
                    break;
            }
        }
        /* for moving car, show blue dot */
        else if ((this.props.car !== undefined && this.props.car.state !== undefined && this.props.car.state === 'moving') || (this.props.car !== undefined && this.props.car.status !== undefined && this.props.car.status === 'alive')) {
            info = this.props.car.licensePlate;
            switch (this.props.zoom) {
                case 19:
                    icon = {
                        url: blue,
                        scaledSize: { width: 12, height: 12 },
                        anchor: { x: 6, y: 6 }
                    };
                    break;
                case 20:
                    icon = {
                        url: blue,
                        scaledSize: { width: 20, height: 20 },
                        anchor: { x: 10, y: 10 }
                    };
                    break;
                case 21:
                    icon = {
                        url: blue,
                        scaledSize: { width: 36, height: 36 },
                        anchor: { x: 18, y: 18 }
                    };
                    break;
                default:
                    icon = {
                        url: blue,
                        scaledSize: { width: 12, height: 12 },
                        anchor: { x: 6, y: 6 }
                    };
                    break;
            }
        }

        return (
            <Marker
                ref={(ref) => { this.marker = ref; }}
                position={{ lat: this.props.car.lat, lng: this.props.car.lon }}
                onClick={this.onToggleHandler}
                icon={icon}
            >
                {this.state.isOpen ? (
                    <InfoWindow onCloseClick={this.onToggleHandler}>
                        <span className={classes.info}>{info}</span>
                    </InfoWindow>
                ) : ''}
            </Marker>
        );
    }
}

export default CarMarker;