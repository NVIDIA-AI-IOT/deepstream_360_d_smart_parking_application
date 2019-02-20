import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import { unregister } from './registerServiceWorker';
import { HashRouter } from 'react-router-dom';

/**
 * This file, index.js, is the entry point of React App. 
 */
ReactDOM.render((
    <HashRouter>
        <App />
    </HashRouter>
), document.getElementById('root'));

unregister();
