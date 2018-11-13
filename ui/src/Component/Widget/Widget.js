import React from 'react';

import classes from './Widget.css';

/**
 * Adjust the size of a panel which displays video or 
 * events/anomalies list to fit the screen size.
 */
const widget = (props) => {
    const style = window.innerWidth < 900 ? {
        top: `calc(${props.top}/2)`,
        bottom: props.bottom,
        left: `calc(${props.left}/2)`,
        right: `calc(${props.right}/2)`,
        height: `calc(${props.height} * 0.35)`,
        width: `calc(${props.width}/2)`
    } : {
        top: props.top,
        bottom: props.bottom,
        left: props.left,
        right: props.right,
        height: props.height,
        width: props.width
    }

    return (
        <div className={classes.widget} style={style}>
            {props.children}
        </div>
    );
};

export default widget;