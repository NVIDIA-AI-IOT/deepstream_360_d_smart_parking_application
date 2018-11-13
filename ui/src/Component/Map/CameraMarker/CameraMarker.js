import React, { PureComponent } from 'react';
import { Marker } from 'react-google-maps';

import cameraIcon from '../../../assets/Security_Camera-512.png';

/**
 * The icon represents the link to the video source 
 * recorded by the entrance cameras. 
 */
class CameraMarker extends PureComponent {
    render() {
        let icon;

        switch (this.props.zoom) {
            case 19:
                icon = {
                    url: cameraIcon,
                    scaledSize: { width: 20, height: 20 }
                };
                break;
            case 20:
            case 21:
                icon = {
                    url: cameraIcon,
                    scaledSize: { width: 35, height: 35 }
                };
                break;
            default:
                icon = {
                    url: cameraIcon,
                    scaledSize: { width: 12, height: 12 }
                };
                break;
        }

        /* click the camera icon to show the entry/exit video. */
        let camera = '';
        if (this.props.cameras.length !== 0) {
            camera = this.props.cameras.map((camera, index) => {
                let key = index * Math.random(10).toString();
                return (
                    <Marker
                        key={key}
                        position={{ lat: camera.lat, lng: camera.lon }}
                        icon={icon}
                        onClick={() => this.props.click(camera.link)}
                    />
                );
            });
        }
        return camera;
    }
}

export default CameraMarker;