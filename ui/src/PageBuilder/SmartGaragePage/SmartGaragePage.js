import React, { Component } from 'react';
import moment from 'moment';

import classes from './SmartGaragePage.css';
import overlayImage from '../../assets/X-StrpP1_simpleConverted.png';

import Capacity from '../../Component/Capacity/Capacity';
// import Flip from '../../Component/Flip/Flip';
import ListPanel from '../../Component/ListPanel/ListPanel';
// import Video from '../../Component/Video/Video';
import Widget from '../../Component/Widget/Widget';
import Search from '../../Component/Search/Search';
import Header from '../../Component/Header/Header';
import Footer from '../../Component/Footer/Footer';

/**
 * SmartGaragePage.js is the main page of the garage. 
 * 
 * SmartGaragePage.js consists of five main components: 
 * (1) list window displaying events/anomalies of detected cars; 
 * (2) garage’s KPI information;
 * (3) garage’s ground overlay; 
 * (4) header and footer; 
 * (5) search bar and search function. 
 * 
 * Props, i.e. Google Maps, ground overlay, WebSocket, cameras, and query, 
 * are received and will be lifted to HomeMap.js and then passed down to Map.js. 
 * 
 * Based on the type of video source, there are two modes: live and playback. live mode has 
 * inputs from RTSP video, and playback from pre-recorded videos. For more information, go to 
 * the configuration session in the README.
 * 
 * p.s. The video panel and the flip function are disable in this demo. 
 * The state `isToggle` is used for the flip function.
 */
class SmartGaragePage extends Component {
    state = {
        searchQuery: {},
        // isToggle: false,
        level: this.props.location.defaults.level || null,
        isLive: this.props.location.isLive,
        source: this.props.location.isLive ? this.props.location.live : this.props.location.playback,
        apis: this.props.location.isLive ? this.props.location.live.apis : this.props.location.playback.apis,
        plate: '',
        isTimeValid: true
    }

    searchClickHandler = (q) => {
        this.setState({ searchQuery: q, isTimeValid: q.isTimeValid });
    }

    componentDidMount() {

        /* reflect ui delay */
        let delayTimestamp;

        if (this.state.isLive) {
            delayTimestamp = moment().subtract(this.state.apis.uiDelaySeconds, 's').utc().format();
        }
        else {
            delayTimestamp = moment.utc(this.state.source.webSocket.startTimestamp).subtract(this.state.apis.uiDelaySeconds, 's').utc().format();
        }

        const googlemap = {
            ...this.props.location.googleMap,
            bounds: this.props.location.bounds
        };

        const groundoverlay = {
            level: this.props.location.defaults.level,
            groundImage: overlayImage,
            defaultBounds: this.props.location.groundOverlay.p1Bounds
        };

        const websocket = {
            url: this.state.source.webSocket.url,
            startTimestamp: delayTimestamp,
            garageLevel: this.state.source.webSocket.garageLevel,
            garageId: this.state.source.webSocket.garageId
        };

        const cameras = this.props.location.cameras;

        this.props.getMapInfo(googlemap, groundoverlay, websocket, cameras);
    }

    componentDidUpdate(prevState) {
        /* if search happened in SmartGarage page, pass the query down to ListPanel/Capacity */
        if (window.location.hash === "#/garage" && this.state.searchQuery !== '' && this.state.searchQuery !== undefined && this.state.searchQuery.searchHappened === window.location.hash) {
            let searchQuery = prevState.searchQuery;
            if (searchQuery !== undefined && (this.state.searchQuery.searchText !== searchQuery.searchText || this.state.searchQuery.timeFrom !== searchQuery.timeFrom || this.state.searchQuery.timeTo !== searchQuery.timeTo)) {
                this.setState({ searchQuery: searchQuery, plate: searchQuery.searchText });
            }
        }
    }

    componentWillUnmount() {
        this.props.isCenterWithinBounds('garage', false);
        window.location.hash = '#/home';
    }

    render() {

        let search = (
            <Search
                click={this.searchClickHandler}
                config={this.state.apis}
                location={this.props.location}
                isLive={this.state.isLive}
                diffTime={this.props.diffTime}
            />
        )

        // let toggleStyle = this.state.isToggle ? { transform: 'rotateY(180deg)' } : {};

        let leftPanel, rightPanel;
    
        const styles = {
            green: "green",
            red: "red"
        };

        // let video;
        if (this.props.zoom > 16 && this.props.centerWithin) {
            leftPanel = (
                <Widget left="50px" top="130px" height="750px" width="430px" onClick={() => this.setState({ isToggle: !this.state.isToggle })}>
                    {/* <Flip
                        toggleStyle={toggleStyle}
                        front={ */}
                    <ListPanel
                        isLive={this.state.isLive}
                        config={this.state.apis}
                        searchQuery={this.state.searchQuery}
                        click={this.props.videoClickHandler}
                        clickPlate={this.props.plateClickHandler}
                        /* toggle={() => this.setState({ isToggle: !this.state.isToggle })} */
                        startTimestamp={this.state.source.apis.startTimestamp}
                        diffTime={this.props.diffTime}
                        name="Alerts"
                        otherside="Events"
                        api={this.state.apis.baseurl + this.state.apis.alerts}
                        style={styles.red}
                    />
                    {/* back={ <ListPanel /> } */}
                </Widget>
            );
            rightPanel = (
                <Widget right="50px" top="130px" height="750px" width="430px" onClick={() => this.setState({ isToggle: !this.state.isToggle })}>
                    <ListPanel
                        isLive={this.state.isLive}
                        config={this.state.apis}
                        searchQuery={this.state.searchQuery}
                        click={this.props.videoClickHandler}
                        clickPlate={this.props.plateClickHandler}
                        /* toggle={() => this.setState({ isToggle: !this.state.isToggle })} */
                        startTimestamp={this.state.source.apis.startTimestamp}
                        diffTime={this.props.diffTime}
                        name="Events"
                        otherside="Alerts"
                        api={this.state.apis.baseurl + this.state.apis.events}
                        style={styles.green}
                    />
                </Widget>
            );
            // video = (
            //     <Widget right="50px" top="130px" height="750px" width="430px">
            //         <Video video={this.props.video} defaultLink={this.props.location.defaults.video} height={750} width={430} />
            //     </Widget>
            // );
        }

        let kpiWidget = window.innerWidth < 900 ? (
            <Widget bottom="28px" height="100px" width="200%">
                <Capacity
                    isLive={this.state.isLive}
                    config={this.state.apis}
                    api={this.state.apis.baseurl + this.state.apis.kpi}
                    garageLevel={this.state.level}
                    name={this.props.location.name}
                    startTimestamp={this.state.source.apis.startTimestamp}
                    diffTime={this.props.diffTime}
                />
            </Widget>
        ) : (
                <Widget bottom="30px" height="50px" width="100%">
                    <Capacity
                        isLive={this.state.isLive}
                        config={this.state.apis}
                        api={this.state.apis.baseurl + this.state.apis.kpi}
                        garageLevel={this.state.level}
                        name={this.props.location.name}
                        startTimestamp={this.state.source.apis.startTimestamp}
                        diffTime={this.props.diffTime}
                    />
                </Widget>
            );

        return (
            <div>
                <Header type={this.props.user.type} isTimeValid={this.state.isTimeValid}>
                    {search}
                </Header>
                <div className={classes.container}>
                    {leftPanel}
                    {rightPanel}
                    {/*video*/}
                    {kpiWidget}
                </div>
                <Footer user={this.props.user.name} />
            </div>
        );
    }
}

export default SmartGaragePage;