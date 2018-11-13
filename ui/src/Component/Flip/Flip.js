import React from 'react';

import classes from './Flip.css';

/**
 * Flip the panel window to switch between anomalies/events list.
 * 
 * In this demo version, the flip function is disable. 
 * Go to SmartGaragePage.js to enable this function.
 */
const flip = (props) => {
    return (
        <div className={classes.flipContainer} >
            <div className={classes.flipper} style={props.toggleStyle}>
                <div className={classes.front}>
                    {props.front}
                </div>
                <div className={classes.back}>
                    {props.back}
                </div>
            </div>
        </div>
    );
};

export default flip;