import React, { Component } from 'react';
import { FormGroup, FormControl, InputGroup, Button, Glyphicon, Collapse, Row, Col } from 'react-bootstrap';
import moment from 'moment';
import DateTime from 'react-datetime';

import classes from './Search.css';

/**
 * Search.js creates and lifts up the search query, including search text and time. 
 * By default, if the source is pre-recorded video, then the start timestamp has to 
 * be set in the config file beforehand. Otherwise, the current timestamp will be used;
 * 
 * The time interval can be set by users through the calendar on UI;
 * 
 * 2 inputs for search function:
 * - text, e.g. license plate and event types;
 * - the time interval for search;
 * 
 * More on search: 
 * When search occurs, only one space could be typed between two strings in the search bar.
 * Besides, the start timestamp on the calendar has to be sometime ealier than the end time.
 */
class Search extends Component {
    state = {
        searchText: '',
        isLive: this.props.isLive,
        startTimestamp: this.props.isLive ? moment.utc().subtract(this.props.config.alertEventRefreshIntervalSeconds + this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : moment.utc(this.props.config.startTimestamp).subtract(this.props.config.alertEventRefreshIntervalSeconds + this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
        timeFrom: this.props.isLive ? moment.utc().subtract(this.props.config.alertEventRefreshIntervalSeconds + this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : moment.utc(this.props.config.startTimestamp).subtract(this.props.config.alertEventRefreshIntervalSeconds + this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
        timeTo: this.props.isLive ? moment.utc().subtract(this.props.config.alertEventRefreshIntervalSeconds + this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : moment.utc(this.props.config.startTimestamp).subtract(this.props.config.alertEventRefreshIntervalSeconds + this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
        timeNow: this.props.isLive ? moment.utc().subtract(this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : moment.utc().subtract(this.props.diffTime + this.props.config.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
        uiDelaySeconds: this.props.config.uiDelaySeconds,
        hasError: false,
        open: false,
        isTimeValid: true,
        diffTime: this.props.diffTime,
        isCalendar: false
    }

    rtrim = (str) => {
        return str.split(/\s+/);
    }

    comma2space = (str) => {
        return str.toString().replace(/,/g, ' ');
    }

    onChangeHandler = (e) => {
        let value = this.rtrim(e.target.value);
        value = this.comma2space(value);
        this.setState({ searchText: value });
    }

    fromChangeHandler = (time) => {
        /* if from is same/before to,throw no error */
        if (moment.utc(time).isSameOrBefore(this.state.timeTo)) {
            this.setState({ timeFrom: moment.utc(time), hasError: false });
        }
        /* if from is after to, throw error */
        else {
            this.setState({ hasError: true });
        }
        this.setState({ isCalendar: true });
    }

    toChangeHandler = (time) => {
        /* if to is after from && to is same/before now, throw no error */
        if (moment.utc(time).isSameOrAfter(this.state.timeFrom)) {
            this.setState({ timeTo: moment.utc(time), hasError: false });
        }
        /* if to is before from, set from/to the same as to */
        else {
            this.setState({ timeTo: moment.utc(time), timeFrom: moment.utc(time), hasError: false });
        }
        this.setState({ isCalendar: true });
    }

    searchClickHandler = () => {
        /* create the query which will be sent to App.js */

        let currentTimeUpdate = this.props.isLive ? moment.utc().subtract(this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : moment.utc().subtract(this.state.diffTime + this.state.uiDelaySeconds, 's').format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');

        let sanityTimeCheck;

        if (this.props.isLive) {
            sanityTimeCheck = moment.utc(this.state.timeFrom).isSameOrBefore(moment.utc(this.state.timeTo)) && moment.utc(this.state.timeTo).isSameOrBefore(moment.utc(currentTimeUpdate));
        }
        else {
            sanityTimeCheck = moment.utc(this.state.timeFrom).isSameOrBefore(moment.utc(this.state.timeTo)) && moment.utc(this.state.timeFrom).isSameOrAfter(this.state.startTimestamp) && moment.utc(this.state.timeTo).isSameOrBefore(moment.utc(currentTimeUpdate));
        }

        let searchQuery = {
            searchText: this.state.searchText,
            timeFrom: moment.utc(this.state.timeFrom).format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
            timeTo: moment.utc(this.state.timeTo).format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
            searchHappened: window.location.hash,
            isTimeValid: sanityTimeCheck,
            isCalendar: this.state.isCalendar,
        };

        this.props.click(searchQuery);  

        this.setState({
            timeFrom: moment.utc(currentTimeUpdate).format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
            timeTo: moment.utc(currentTimeUpdate).format('YYYY-MM-DDTHH:mm:ss.SSS[Z]'),
            open: false,
            isCalendar: false
        });

    }

    reloadPage = () => {
        window.location.reload(false);    
    }

    render() {
        let search;

        if (this.state.hasError) {
            search = (
                <Button type="button" className={this.state.open ? classes.button1 : classes.button} onClick={this.reloadPage} disabled>
                    <Glyphicon glyph="search" className={classes.glyphicon} />
                </Button>
            );
        }
        else {
            search = (
                <Button type="button" disabled={this.state.hasError} className={this.state.open ? classes.button1 : classes.button} onClick={this.searchClickHandler}>
                    <Glyphicon glyph="search" className={classes.glyphicon} />
                </Button>
            );
        }

        let openCalendar = window.innerWidth < 900 ? null : true;

        /* input search text and time */
        return (
            <FormGroup>
                <InputGroup className={this.state.open ? classes.input1 : classes.input} >
                    {/* input area */}
                    <FormControl
                        type="text"
                        value={this.state.searchText}
                        onChange={this.onChangeHandler}
                        onKeyPress={event => {
                            if (event.key === 'Enter') {
                                this.searchClickHandler();
                            }
                        }} />
                    {/* expand button */}
                    <InputGroup.Button>
                        <Button type="button" className={classes.buttonbetween} onClick={() => this.setState({ open: !this.state.open })}>
                            <Glyphicon glyph="triangle-bottom" className={classes.glyphicon} />
                        </Button>
                    </InputGroup.Button>
                    {/* search button */}
                    <InputGroup.Button>
                        {search}
                    </InputGroup.Button>
                </InputGroup>
                <Collapse in={this.state.open} >
                    <Row className={classes.collapse}>
                        <Col md={5} sm={5}>
                            <DateTime
                                open={openCalendar}
                                dateFormat='YYYY-MM-DD'
                                timeFormat='HH:mm:ss'
                                value={moment(this.state.timeFrom).local().format('YYYY-MM-DD HH:mm:ss')}
                                onChange={this.fromChangeHandler}
                                isValidDate={(current) => { return this.props.isLive ? current.isSameOrBefore(this.state.timeTo, 'date') : current.isSameOrBefore(this.state.timeTo, 'date') && current.isSameOrAfter(this.state.startTimestamp, 'date') }}
                            />
                        </Col>
                        <Col md={2} className={classes.timespan} sm={2}>TO</Col>
                        <Col md={5} sm={5}>
                            <DateTime
                                open={openCalendar}
                                dateFormat='YYYY-MM-DD'
                                timeFormat='HH:mm:ss'
                                value={moment(this.state.timeTo).local().format('YYYY-MM-DD HH:mm:ss')}
                                onChange={this.toChangeHandler}
                                isValidDate={(current) => { return this.props.isLive ? current.isSameOrBefore(this.state.timeNow, 'date') && current.isSameOrAfter(this.state.timeFrom, 'date') : current.isSameOrAfter(this.state.timeFrom, 'date') && current.isSameOrBefore(this.state.timeNow, 'date') }}
                            />
                        </Col>
                    </Row>
                </Collapse>
            </FormGroup>
        );
    }
}

export default Search;