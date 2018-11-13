import React from 'react';
import Moment from 'moment';

import Aux from '../../../Hoc/Auxiliary/Auxiliary';
import classes from './Item.css';

/**
 *  Details of anomalies/events thumbnail shown in the panel window. 
 */
const item = (props) => {
    let item = [];
    let br = window.innerWidth < 900 ? <br /> : null;
    if (props.list['@timestamp'] !== null && props.list['@timestamp'] !== undefined) {
        item.push(Moment(props.list['@timestamp']).local().format('YY-MM-DD HH:mm:ss.SSS'));
    }
    if (props.list.license !== null && props.list.license !== undefined) {
        item.push(<Aux key="1">&nbsp;|&nbsp;<a className={classes.license} onClick={() => props.clickPlate(props.list.license)}>{props.list.license}</a></Aux>);
    }
    if (props.list.description !== null && props.list.description !== undefined) {
        item.push(<Aux key="2">&nbsp;|{br}&nbsp;{props.list.description}</Aux>);
    }
    if (props.list.type !== null && props.list.type !== undefined) {
        item.push(<Aux key="3">&nbsp;|{br}&nbsp;{props.list.type}</Aux>);
    }
    if (props.list.entryVideo !== null && props.list.entryVideo !== undefined && props.list.entryVideo !== '') {
        item.push(<Aux key="4">&nbsp;|&nbsp;<a onClick={() => props.click(props.list.entryVideo)}>entryVideo</a></Aux>);
    }
    if (props.list.exitVideo !== null && props.list.exitVideo !== undefined && props.list.exitVideo !== '') {
        item.push(<Aux key="5">&nbsp;|&nbsp;<a onClick={() => props.click(props.list.exitVideo)}>exitVideo</a></Aux>);
    }
    if (props.list.videoPath !== null && props.list.videoPath !== undefined && props.list.videoPath !== '') {
        item.push(<Aux key="6">&nbsp;|&nbsp;<a onClick={() => props.click(props.list.videoPath)}>video</a></Aux>);
    }

    let li;
    if (props.style === 'red') {
        li = <li className={classes.red}>{item}</li>;
    }
    else if (props.style === 'green') {
        li = <li className={classes.green}>{item}</li>;
    }

    return li;
};

export default item;