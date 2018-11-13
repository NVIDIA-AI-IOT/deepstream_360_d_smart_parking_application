import React from 'react';
import { Player, BigPlayButton } from 'video-react';
import HLSSource from './HLS';

/**
 * Add customized HLSSource component into video-react player.
 * The component with `isVideoChild` attribute will be added into `Video` component.
 * Please use this url if you test it from local:
 * http://www.streambox.fr/playlists/x36xhzz/x36xhzz.m3u8
 */
export default (props) => {
  return (
    <Player muted={true}>
      <HLSSource
        isVideoChild
        src={props.link}
      />
      <BigPlayButton disabled />
    </Player>
  );
};