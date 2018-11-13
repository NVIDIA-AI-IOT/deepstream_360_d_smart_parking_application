'use strict';

var server = require('./initializers/server');
var winston = require('winston');
var logger = winston.createLogger({
  transports: [
    new (winston.transports.Console)({ 'timestamp': true })
  ],
  exitOnError: false
});

logger.info('[APP] Starting server initialization');

// Initialize the server

server(function(err){
  if (err) {
    logger.error('[APP] initialization failed', err);
  } else {
    logger.info('[APP] initialized SUCCESSFULLY');
  }
})
