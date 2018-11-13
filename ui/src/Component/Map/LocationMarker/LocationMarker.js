import React, { Component } from 'react';
import { Marker } from 'react-google-maps';

import locationIcon from '../../../assets/mm.png';

/**
 * The icon represents the location of the garage 
 * on the homepage of the UI.
 */
class LocationMarker extends Component {

    onClickHandler = (url) => {
        window.location.hash = "#/" + url;
    }

    render() {
        let icon;

        switch (this.props.zoom) {
            case 10:
            case 11:
            case 12:
                icon = {
                    url: locationIcon,
                    scaledSize: { width: 20, height: 20 }
                };
                break;
            case 13:
            case 14:
                icon = {
                    url: locationIcon,
                    scaledSize: { width: 40, height: 40 }
                };
                break;
            case 15:
            case 16:
            case 17:
            case 18:
                icon = {
                    url: locationIcon,
                    scaledSize: { width: 80, height: 80 }
                };
                break;
            default:
                icon = '';
                break;
        }

        let location = this.props.locations.map((location, index) => {
            return (
                <Marker
                    key={index}
                    position={{ lat: location[Object.getOwnPropertyNames(location)[1]], lng: location[Object.getOwnPropertyNames(location)[2]] }}
                    icon={icon}
                    onClick={() => this.onClickHandler(location[Object.getOwnPropertyNames(location)[0]])}
                />
            );
        });

        return location;
    }
}

export default LocationMarker;