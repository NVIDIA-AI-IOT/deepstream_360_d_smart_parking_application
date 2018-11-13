import React, { Component } from 'react';
import Moment from 'moment';
import { Tooltip, OverlayTrigger } from 'react-bootstrap';

import Axios from 'axios';

import classes from './ListPanel.css';

import Item from './PanelItem/Item';

/**
 * ListPanel.js displays messages of car events/anomalies on the UI during a certain time period. 
 * To update the list, query will be sent to the backend every `alertEventRefreshIntervalSeconds` secs;
 * 
 * Search without calendar will be refreshed every `alertEventRefreshIntervalSeconds` secs;
 * 
 * `autoRefreshIntervalMinutes` is used for the playback to play the pre-recoded video. 
 * In playback mode, the browser will auto refresh every `autoRefreshIntervalMinutes` mins. 
 * Both `alertEventRefreshIntervalSeconds` and `autoRefreshIntervalMinutes` are configurable, 
 * and their default settings are 5 secs and 30 mins respectively; 
 * 
 * Configurable variables: `alertEventRefreshIntervalSeconds`, `autoRefreshIntervalMinutes`
 */
class ListPanel extends Component {
    state = {
        anomalyList: [],
        searchList: [],
        apiInterval: null,
        searchInterval: null,
        live: true,
        needToken: false,
        timeTo: this.props.isLive ? "" : Moment.utc(this.props.startTimestamp).subtract(this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
        preStartTimestamp: this.props.isLive ? '' : Moment.utc(this.props.startTimestamp).subtract(this.props.config.alertEventRefreshIntervalSeconds + this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
        alertEventListLength: this.props.config.alertEventListLength,
        alertEventRefreshIntervalSeconds: this.props.config.alertEventRefreshIntervalSeconds,
        autoRefreshIntervalMinutes: this.props.config.autoRefreshIntervalMinutes,
        uiDelaySeconds: this.props.config.uiDelaySeconds,
        isSearch: false,
        diffTime: this.props.diffTime,
        firstSearch: true
    }

    /* format time query */

    getTimequery = () => {
        let T1, T2;
        /* if there is a search... */
        if (Object.keys(this.props.searchQuery).length !== 0) {
            /* live mode */
            if (this.props.isLive) {
                /* without calendar */
                if (!this.props.searchQuery.isCalendar) {
                    /* for alerts, always query the time from the startTimestamp */
                    if (this.props.name === "Alerts" || this.state.firstSearch) {
                        this.setState({ firstSearch: false });
                        return '@timestamp: [* TO ' + Moment.utc().subtract(this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') + ']';
                    }
                    else {
                        T2 = Moment.utc().subtract(this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
                        T1 = Moment.utc(this.state.timeTo).format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
                        this.setState({ timeTo: T2 });
                        return '@timestamp:[' + T1 + ' TO ' + T2 + ']';
                    }
                }
                /* with calendar */
                else {
                    return '@timestamp:[' + this.props.searchQuery.timeFrom + ' TO ' + this.props.searchQuery.timeTo + ']';
                }
            }
            /* playback mode */
            else {
                /* without calendar */
                if (!this.props.searchQuery.isCalendar) {
                    if (this.props.name === "Alerts" || this.state.firstSearch) {
                        this.setState({ firstSearch: false });
                        return '@timestamp:[' + this.state.preStartTimestamp + ' TO ' + Moment.utc().subtract(this.state.diffTime + this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') + ']';
                    }
                    else {
                        T2 = Moment.utc().subtract(this.state.diffTime + this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
                        T1 = Moment.utc(this.state.timeTo).format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
                        this.setState({ timeTo: T2 });
                        return '@timestamp:[' + T1 + ' TO ' + T2 + ']';
                    }
                }
                /* with calendar */
                else {
                    return '@timestamp:[' + this.props.searchQuery.timeFrom + ' TO ' + this.props.searchQuery.timeTo + ']';
                }
            }
        }
    }

    /* reformat incoming data to plain array of objects */
    getObjs = (obj, keys, newArrObj) => {
        for (let i = 0; i < keys.length; i++) {
            if (typeof (obj[keys[i]]) === 'string') {
                newArrObj.push({ [keys[i]]: obj[keys[i]] });
            }
            else if (typeof (obj[keys[i]]) === 'object') {
                if (obj[keys[i]] === null) {
                    newArrObj.push({ [keys[i]]: '' });
                }
                else {
                    this.getObjs(obj[keys[i]], Object.getOwnPropertyNames(obj[keys[i]]), newArrObj);
                }
            }
            else {
                newArrObj.push({ [keys[i]]: '' });
            }
        }
        return newArrObj;
    }

    apiAutoRefresh = () => {

        let timestamp;

        let T2 = this.props.isLive ? Moment.utc().subtract(this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : Moment.utc().subtract(this.state.diffTime + this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
        /* for alerts, no need to append the data because the start time query is from the startTimestamp */
        if (this.props.name === "Alerts") {
            if (this.props.isLive) {
                timestamp = '@timestamp:[ * TO ' + T2 + ']';
            }
            else {
                timestamp = '@timestamp:[' + this.state.preStartTimestamp + ' TO ' + T2 + ']';
            }
        }
        else {
            let T1 = Moment.utc(this.state.timeTo).format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
            timestamp = '@timestamp:[' + T1 + ' TO ' + T2 + ']';
        }

        let request = timestamp;

        Axios.get(this.props.api, {
            params: {
                q: null,            
                timeQuery: request, 
                isSearch: false
            },
            cancelToken: this.source.token
        }).then(res => {
            let newObj = res.data.length !== 0 ? res.data.map((data) => {
                return Object.assign({}, ...this.getObjs(data._source, Object.getOwnPropertyNames(data._source), []));
            }) : [];
            if (this.props.name !== "Alerts" && newObj.length < this.state.alertEventListLength) {
                let numberOfObjectsRequired = this.state.alertEventListLength - newObj.length;
                let requiredOldObjects = [...this.state.anomalyList].slice(0, numberOfObjectsRequired);
                for (let oldObject of requiredOldObjects) {
                    newObj.push(oldObject);
                }
            }
            this.setState({ anomalyList: newObj, needToken: false, timeTo: T2 });
        }).catch((thrown) => {
            if (Axios.isCancel(thrown)) {
                console.log('Request canceled', thrown.message);
            }
            else {
                console.log(thrown.message);
                console.log('something wrong with 5s interval panel ajax');
            }
        });
    }

    doSearch = () => {
        let searchText = this.props.searchQuery.searchText === '' ? '' : this.props.searchQuery.searchText.trim();
        let timeQuery = this.getTimequery();

        Axios.get(this.props.api, {
            params: {
                q: searchText.length === 0 ? null : searchText,    
                timeQuery: timeQuery,   
                isSearch: true
            },
            cancelToken: this.source.token
        }).then(res => {
            let newObj = res.data.length !== 0 ? res.data.map((data) => {
                return Object.assign({}, ...this.getObjs(data._source, Object.getOwnPropertyNames(data._source), []));
            }) : [];
            this.setState({ searchList: newObj.slice(0, this.state.alertEventListLength) });
        }).catch((thrown) => {
            if (Axios.isCancel(thrown)) {
                console.log('Request canceled', thrown.message);
            }
            else {
                console.log('something wrong with search panel ajax');
            }
        });

        if (!this.props.searchQuery.isCalendar) {
            this.searchInterval = setInterval(() => {

                let searchText = this.props.searchQuery.searchText === '' ? '' : this.props.searchQuery.searchText.trim();
                let timeQuery = this.getTimequery();

                Axios.get(this.props.api, {
                    params: {
                        q: searchText.length === 0 ? null : searchText,
                        timeQuery: timeQuery,
                        isSearch: true
                    },
                    cancelToken: this.source.token
                }).then(res => {

                    let newObj = res.data.length !== 0 ? res.data.map((data) => {
                        return Object.assign({}, ...this.getObjs(data._source, Object.getOwnPropertyNames(data._source), []));
                    }) : [];
                    if (this.props.name !== "Alerts" && newObj.length < this.state.alertEventListLength) {
                        let numberOfObjectsRequired = this.state.alertEventListLength - newObj.length;
                        let requiredOldObjects = [...this.state.searchList].slice(0, numberOfObjectsRequired);
                        for (let oldObject of requiredOldObjects) {
                            newObj.push(oldObject);
                        }
                    }
                    this.setState({ searchList: newObj });
                }).catch((thrown) => {
                    if (Axios.isCancel(thrown)) {
                        console.log('Request canceled', thrown.message);
                    }
                    else {
                        console.log('something wrong with search panel ajax');
                    }
                });

            }, this.state.alertEventRefreshIntervalSeconds * 1000);

            this.setState({ searchInterval: this.searchInterval });
        }
    }

    componentDidMount() {
        this.source = Axios.CancelToken.source();

        if (this.props.api !== '') {

            let start = this.props.isLive ? Moment.utc().subtract(this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : Moment.utc().subtract(this.state.diffTime + this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
            let prestart = Moment.utc(start).subtract(this.state.alertEventRefreshIntervalSeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
            let timestamp = '@timestamp:[' + prestart + ' TO ' + start + ']';
            let request = timestamp;

            let url = this.props.api;

            Axios.get(url, {
                params: {
                    q: null,
                    timeQuery: request,
                    isSearch: false
                },
                cancelToken: this.source.token
            }).then(res => {
                /* assign res.data as array of objects */
                let newObj = res.data.length !== 0 ? res.data.map((data) => {
                    return Object.assign({}, ...this.getObjs(data._source, Object.getOwnPropertyNames(data._source), []));
                }) : [];
                this.setState({ anomalyList: newObj.slice(0, this.state.alertEventListLength), timeTo: start });

            }).catch((thrown) => {
                if (Axios.isCancel(thrown)) {
                    console.log('Request canceled', thrown.message);
                }
                else {
                    console.log('something wrong with panel ajax');
                }
            });

            /* compress events. if lots of same car moving events, shown only latest; entry and exit shown seperately */
            this.interval = setInterval(() => this.apiAutoRefresh(), this.state.alertEventRefreshIntervalSeconds * 1000);

            this.setState({ apiInterval: this.interval });

            /* auto refresh the webpage */
            if (!this.props.isLive) {
                this.timeout = setTimeout(() => {
                    window.location.reload();
                }, this.state.autoRefreshIntervalMinutes * 60 * 1000);
            }
        }
    }

    componentDidUpdate(prevProps, prevState) {

        /* if there is a search query, and time/text is changed, and there is an api */
        if (Object.keys((this.props.searchQuery)).length !== 0 && (prevProps.searchQuery.timeFrom !== this.props.searchQuery.timeFrom || prevProps.searchQuery.timeTo !== this.props.searchQuery.timeTo) && this.props.api !== '') {

            clearInterval(this.interval);
            clearInterval(this.searchInterval);
            if (this.props.searchQuery.isTimeValid) {
                this.setState({ live: false, apiInterval: null, searchInterval: null, firstSearch: true }, () => this.doSearch());
            }
            else {
                this.setState({ live: true, apiInterval: null, searchInterval: null }, () => { this.interval = setInterval(() => this.apiAutoRefresh(), this.state.alertEventRefreshIntervalSeconds * 1000); this.setState({ apiInterval: this.interval }) });
            }

        }
    }

    componentWillUnmount() {
        clearInterval(this.interval);
        clearInterval(this.searchInterval);
        if (this.socket !== undefined) {
            this.socket.disconnect();
        }
    }

    render() {
        let items, liveButton;

        /* if it is live status, loop through live list */
        if (this.state.live) {
            items = this.state.anomalyList.map((singleData, index) => {
                return <Item key={index} style={this.props.style} list={singleData} clickPlate={this.props.clickPlate} click={this.props.click} />;
            });
        }
        /* if search happens, loop through search list, add back-to-live button */
        else {
            items = this.state.searchList.map((singleData, index) => {
                return <Item key={index} style={this.props.style} list={singleData} clickPlate={this.props.clickPlate} click={this.props.click} />;
            });
            liveButton = (
                <div className={classes.live}>
                    <OverlayTrigger placement='right' overlay={<Tooltip id="tooltip" className={classes.tip}>Go back Live</Tooltip>} >
                        <a onClick={() => { this.setState({ live: true, searchInterval: null }); clearInterval(this.searchInterval); this.interval = setInterval(() => this.apiAutoRefresh(), this.state.alertEventRefreshIntervalSeconds * 1000); this.setState({ apiInterval: this.interval }) }}>L</a>
                    </OverlayTrigger>
                </div>
            );
        }

        return (
            <div className={classes.alerts}>
                <p className={classes.timestamp}>Latest update: {this.props.isLive ? Moment().local().subtract(this.state.uiDelaySeconds, 's').format('YYYY-MM-DD HH:mm:ss') : Moment().local().subtract(this.state.diffTime + this.state.uiDelaySeconds, 's').format('YYYY-MM-DD HH:mm:ss')}</p>
                <div className={classes.title}>
                    {/*<OverlayTrigger placement='top' overlay={<Tooltip id="tooltip" className={classes.tip}>Click to see {this.props.otherside}</Tooltip>} >
                    <span className={classes.toggle} onClick={this.props.toggle}>{this.props.name}</span>
                    </OverlayTrigger>*/}
                    <span>{this.props.name}</span>
                </div>
                {liveButton}
                <div className={classes.list}>
                    <ul className={classes.nvidiaList}>
                        {items}
                    </ul>
                </div>
            </div>
        );
    }
}

export default ListPanel;