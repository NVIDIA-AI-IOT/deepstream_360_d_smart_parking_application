import React, { Component } from 'react';

import classes from './Video.css';

import Item from '../ListPanel/Item/Item';
import StreamVideo from './StreamVideo/StreamPlayer';

/**
 * Import videos from four different sources, i.e.
 * 1) Camera icon on the map;
 * 2) Video link in the panel window;
 * 3) Pre-recorded video in the playback mode;
 * 4) RTSP video stream in the live mode.
 */
class Video extends Component {
    state = {
        pause: false
    }

    onClickHandler = () => {
        if (this.state.pause) {
            this.videoplayer.pause();
        }
        else {
            this.videoplayer.play();
        }
        this.setState({ pause: !this.state.pause });
    }

    componentDidUpdate() {
        if (this.props.seconds !== undefined && this.videoplayer !== undefined) {
            this.videoplayer.currentTime = this.props.seconds;
        }
    }

    render() {
        let player, message;
        let link;
        /* video object comes from alerts/events panel. */
        if (this.props.video !== undefined && typeof (this.props.video) === 'object' && ((this.props.video.entryVideo !== null && this.props.video.entryVideo !== undefined && this.props.video.entryVideo !== '') || (this.props.video.exitVideo !== null && this.props.video.exitVideo !== undefined && this.props.video.exitVideo !== '') || (this.props.video.videoPath !== null && this.props.video.videoPath !== undefined && this.props.video.videoPath !== '') || (this.props.video.clip !== null && this.props.video.clip !== undefined && this.props.video.clip !== ''))) {
            link = this.props.video.entryVideo || this.props.video.exitVideo || this.props.video.videoPath || this.props.video.clip;
        }
        /* video link comes from map(camera) */
        else if (this.props.video !== undefined && typeof (this.props.video) === 'string' && this.props.video !== '' && this.props.video !== null) {
            link = this.props.video;
        }
        else {
            link = this.props.defaultLink;
        }

        let width = window.innerWidth < 900 ? this.props.width / 2 : this.props.width;
        let height = window.innerWidth < 900 ? this.props.height * 0.4 : this.props.height;

        /* if it is pre-recorded video */
        if (link.endsWith('mp4') || link.endsWith('webm') || link.endsWith('ogv')) {
            if (link.endsWith('clip5min_smaller.mp4')) {
                player = (
                    <video
                        ref={(el) => { this.videoplayer = el }}
                        controls
                        width={this.props.width}
                        height={this.props.height}
                        src={link}
                        onClick={this.onClickHandler}
                        onSuspend={() => { this.videoplayer.play() }}
                    />
                );
            }
            else {
                player = (
                    <video
                        ref={(el) => { this.videoplayer = el }}
                        controls
                        width={width}
                        height={height - 50}
                        src={link}
                        onClick={this.onClickHandler}
                        onSuspend={() => { this.videoplayer.play() }}
                    />
                );
                message = (
                    <Item list={this.props.video} />
                );
            }
        }
        /* stream video */
        else {
            player = <StreamVideo link={link} height={this.props.height} width={this.props.width} />;
        }

        return (
            <div className={classes.videoContainer}>
                <div className={classes.player}>
                    {player}
                    {message}
                </div>
            </div>
        );
    }
}

export default Video;

