import React from 'react';
import FontAwesomeIcon from '@fortawesome/react-fontawesome';
import { faQuestionCircle, faExclamationTriangle } from '@fortawesome/free-solid-svg-icons';
import { Navbar, Nav, NavItem } from 'react-bootstrap';
import { Tooltip, OverlayTrigger } from 'react-bootstrap';

import classes from './Header.css';
import logo from '../../assets/NVLogo-H-White-Small.png';

/**
 * Header.js contains
 * 1) nvidia's logo;
 * 2) app's name;
 * 3) search bar with drop-down calendar; 
 * 4) alert icon which is an exclamation triangle will be triggered by invalid time bounds in search; 
 * 5) question mark icon without hyperlink;
 * 6) tool icon without hyperlink.
 */
const header = (props) => {
    let alertIcon;

    if ( window.location.hash === "#/home" || props.isTimeValid ) {
        alertIcon = (          
                <Nav pullRight >
                    <NavItem>
                        {null}
                    </NavItem>
                </Nav>         
            ); 
    }
    else {
        alertIcon = (
        <OverlayTrigger placement='left' overlay={<Tooltip id="tooltip" >Invalid time</Tooltip>} >
            <Nav pullRight >
                <NavItem>
                    <FontAwesomeIcon icon={faExclamationTriangle} color="red" />
                </NavItem>
            </Nav>
        </OverlayTrigger>            
        );
    }

    return (
        <Navbar inverse fixedTop fluid className={classes.Header}>
            <Navbar.Header>
                {/* left nvidia brand */}
                <Navbar.Brand>
                    <a href="/">
                        <img alt="Nvidia" src={logo} />
                    </a>
                </Navbar.Brand>
                {/* center METROPOLIS text */}
                <Navbar.Brand className={classes.center}>METROPOLIS</Navbar.Brand>
                <Navbar.Toggle />
            </Navbar.Header>
            <Navbar.Collapse>
                {/* right end question to other websites */}
                <Nav pullRight>
                    <NavItem className={classes.questioncircle}>
                        <FontAwesomeIcon icon={faQuestionCircle} />
                    </NavItem>
                </Nav>
                {/* alert icon if time query is invalid */}
                {alertIcon}
                {/* search input group */}
                <Navbar.Form pullRight style={{ textAlign: 'right' }}>
                    {props.children}
                </Navbar.Form>
            </Navbar.Collapse>
        </Navbar>
    );
};

export default header;