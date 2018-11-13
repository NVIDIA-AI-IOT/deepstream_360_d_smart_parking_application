import React from 'react';
import Moment from 'moment';

import Aux from '../../../Hoc/Auxiliary/Auxiliary';
import classes from './Item.css';

/**
 * Details of anomalies/events thumbnail shown in the video window.
 */  
const item = (props) => {
    let item = [];
    if(props.list !== undefined) {
        if(window.location.hash === '#/garage'){
            if(props.list['@timestamp'] !== null && props.list['@timestamp'] !== undefined) {
                item.push(Moment(props.list['@timestamp']).local().format('YY-MM-DD HH:mm:ss.SSS'));
            }
            if(props.list.license !== null && props.list.license !== undefined) {
                if(props.clickable){
                    item.push(<Aux key="license">&nbsp;|&nbsp;<a className={classes.license} onClick={() => props.clickPlate(props.list.license)}>{props.list.license}</a></Aux>);     
                }
                else {
                    item.push(<Aux key="license">&nbsp;|&nbsp;<span className={classes.span}>{props.list.license}</span></Aux>);     
                }
            }
            if(props.list.description !== null && props.list.description !== undefined) {
                item.push(<Aux key="description">&nbsp;|&nbsp;<br/>{props.list.description}</Aux>);
            }
        }
    }

    return (
        <div className={classes.message}>
            {item}
        </div>
    );
};

export default item;