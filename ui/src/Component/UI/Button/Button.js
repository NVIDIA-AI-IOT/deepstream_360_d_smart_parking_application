import React from 'react';
import { Button } from 'react-bootstrap';

import classes from './Button.css';


const button = ({bsStyle, bsSize, ...props}) => {
    let btnStyle;
    switch(bsStyle) {
        case 'primary':
            btnStyle = classes.primary;
            break;
        case 'danger':
            btnStyle = classes.danger;
            break;
        case undefined:
        case 'default':
        default:
            btnStyle = classes.default;
            break;
    }
    return (
        <Button
            className={btnStyle}
            bsSize={bsSize === undefined ? null : bsSize}
            {...props}
        >
            {props.children}
        </Button>
    );
};

export default button;