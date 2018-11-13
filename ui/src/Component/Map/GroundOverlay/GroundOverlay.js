import React from 'react';
import { GroundOverlay } from 'react-google-maps';


const groundOverlay = (props) => {
    /* the bounds of the garage on the google map */
    return (
        <GroundOverlay
            key="P1"
            defaultUrl={props.groundoverlay.groundImage}
            defaultBounds={
                {
                    north: props.groundoverlay.defaultBounds.north,
                    south: props.groundoverlay.defaultBounds.south,
                    east: props.groundoverlay.defaultBounds.east,
                    west: props.groundoverlay.defaultBounds.west
                }
            }
        />
    );
};

export default groundOverlay;