import React from 'react';
import { Navbar } from 'react-bootstrap';

import classes from './Footer.css';

/**
 * Footer.js contains four elements: 
 * (1) app’s name; 
 * (2) app’s version; 
 * (3) user’s information; 
 * (4) notices. 
 */
const footer = (props) => {
    /* show information on the footer */
    return (
        <Navbar fluid fixedBottom className={classes.footer}>
            <div className={classes.footercontainer}>
                <span>METROPOLIS</span> | <span>Ver: beta</span> | <span>User: {props.user}</span> | <span>This is a virtual garage for demo only.</span>
            </div>
        </Navbar>
    );
};

export default footer;