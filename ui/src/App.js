import React, { Component } from 'react';
import { Switch, Route, Redirect } from 'react-router-dom';
import Axios from 'axios';
import { Offline } from 'react-detect-offline';
//import Moment from 'moment';

import classes from './App.css';

import HomeMap from './PageBuilder/HomeMap';
import Loader from './Component/UI/Loader/Loader';

/**
 * 4 Main tasks:
 * 1) read the config file and get the environment variables;
 * 2) pass down the props, i.e. environment variables;
 * 3) declare the routes for home/garage page;
 * 4) offline detection. 
 */
class App extends Component {
  state = {
    envVar: {}
  }

  componentDidMount() {
    this.source = Axios.CancelToken.source();
    /* query the REST API to retrieve configuration information. */
    Axios.get('http://' + process.env.REACT_APP_BACKEND_IP_ADDRESS + ':' + process.env.REACT_APP_BACKEND_PORT + '/ui-config')
      .then((res) => {
        /* copy the configuration into envVar */
        const envVar = res.data;
        this.setState({ envVar: envVar });
      })
      .catch(err => {
        this.setState({
          err: err.message
        });
      })
  }

  componentWillUnmount() {
    this.source.cancel('Operation canceled by the user');
    clearInterval(this.interval);
  }

  render() {
    if (this.state.envVar !== undefined && Object.keys(this.state.envVar).length !== 0) {
      return (
        <div>
          <Offline>
            <div className={classes.offline}> You are offline! Please refresh the page when you are online again.</div>
          </Offline>
          <Switch>
            {/* /garage focuses the googlemap on a particular garage */}
            <Route exact path="/garage" render={() =>
              <HomeMap
                locations={this.state.envVar}
                zoom={19}
                path={window.location.hash}
                centerWithin={{ name: 'garage', bool: true }}
              />}
            />
            {/* /home takes googlemap page with one or more markers */}
            <Route exact path="/home" render={() => <HomeMap locations={this.state.envVar} />} />
            <Redirect to="/home" />
          </Switch>
        </div>
      );
    }
    else {
      return (
        <div className={classes.loading}>
          <Loader />
          {this.state.err}
        </div>
      );
    }
  }
}

export default App;