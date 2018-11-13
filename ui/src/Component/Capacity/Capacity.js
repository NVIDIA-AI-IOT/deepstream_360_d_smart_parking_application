import React, { Component } from 'react';
import Moment from 'moment';
import { Row, Col } from 'react-bootstrap';
import Axios from 'axios';

import classes from './Capacity.css';

/**
 * Get the KPI (or capacity) of the garage by sending the Ajax query to the backend 
 * every `alertEventRefreshIntervalSeconds` secs. It's default value is 5 secs.
 * 
 * KPI information includes available/occupied parking spots, and entry/exit flow;
 * 
 * Configurable variable: `alertEventRefreshIntervalSeconds`
 */
class Capacity extends Component {
    state = {
        id: '',
        stats: [],
        isLive: this.props.isLive,
        alertEventRefreshIntervalSeconds: this.props.config.alertEventRefreshIntervalSeconds,
        startTimestamp: this.props.isLive ? Moment.utc().subtract(this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : Moment.utc(this.props.startTimestamp).subtract(this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
        uiDelaySeconds: this.props.config.uiDelaySeconds,
        diffTime: this.props.diffTime
    }

    componentDidMount() {

        this.source = Axios.CancelToken.source();
        /* api call needed */
        if (this.props.api !== '') {

            /* create the query */
            const start = this.props.isLive ? Moment.utc().subtract(this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : Moment.utc().subtract(this.state.diffTime + this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
            let prestart = Moment.utc(start).subtract(this.state.alertEventRefreshIntervalSeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
            let timestamp = this.state.isLive ? '@timestamp:[* TO ' + start + ']' : '@timestamp:[' + prestart + ' TO ' + start + ']';
            let request = timestamp;

            Axios.get(this.props.api, {
                params: {
                    timeQuery: request 
                },
                cancelToken: this.source.token
            }).then((res) => {
                let obj = res.data;
                let stats = [];
                for (let key in obj) {
                    let value = obj[key];
                    stats.push({ key, value });
                }
                this.setState({ id: res.data['id'], stats: stats.splice(1) });
            })
                .catch((thrown) => {
                    if (Axios.isCancel(thrown)) {
                        console.log('Request canceled', thrown.message);
                    }
                    else {
                        console.log('something wrong with KPI ajax');
                    }
                });
            /* make ajax call every alertEventRefreshIntervalSeconds seconds */
            this.interval = setInterval(() => {

                let currentTime = this.props.isLive ? Moment.utc().subtract(this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : Moment.utc().subtract(this.state.diffTime + this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
                let timestamp = this.state.isLive ? '@timestamp:[* TO ' + currentTime + ']' : '@timestamp:[' + start + ' TO ' + currentTime + ']';
                let request = timestamp;

                Axios.get(this.props.api, {
                    params: {
                        timeQuery: request 
                    },
                    cancelToken: this.source.token
                }).then((res) => {
                        let obj = res.data;
                        let stats = [];
                        for (let key in obj) {
                            let value = obj[key];
                            stats.push({ key, value });
                        }
                        this.setState({ id: res.data['id'], stats: stats.splice(1) });
                    })
                    .catch((thrown) => {
                        if (Axios.isCancel(thrown)) {
                            console.log('Request canceled', thrown.message);
                        }
                        else {
                            console.log('something wrong with KPI interval ajax');
                        }
                    });
            }, this.state.alertEventRefreshIntervalSeconds * 1000);
        }
    }

    componentWillUnmount() {
        clearInterval(this.interval);
        this.source.cancel('Operation canceled by the user');
        if (this.socket !== undefined) {
            this.socket.disconnect();
        }
    }

    render() {
        /* loop through stats array */
        let col = this.state.stats.map((data, index) => {
            return (
                <Col xs={2} sm={2} key={index}>
                    <span className={classes.num}>{data.value}</span>
                    &nbsp;
                    <span className={classes.spot}>{data.key}</span>
                </Col>
            );
        });

        return (
            <Row className={classes.kpi}>
                <Col xs={2} sm={2} className={classes.title}>{this.props.name}</Col>
                <Col xs={9} sm={9} >
                    <Row className={classes.kpirow}>
                        {col}
                    </Row>
                </Col>

            </Row>
        );
    }
}

export default Capacity;