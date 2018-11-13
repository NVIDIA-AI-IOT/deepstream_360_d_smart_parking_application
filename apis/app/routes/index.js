var changeCase = require('change-case');
var express = require('express');
var routes = require('require-dir')();
var winston = require('winston');
var logger = winston.createLogger({
  transports: [
    new (winston.transports.Console)({ 'timestamp': true })
  ],
  exitOnError: false
});

module.exports = function(app) {
  'use strict';
  
  logger.info('[ROUTES] Initing routers:' + Object.keys(routes));
  
  // Initialize all routes
  Object.keys(routes).forEach(function(routeName) {
    var router = express.Router();
    // You can add some middleware here 
    // router.use(someMiddleware);
  
    logger.info('[ROUTES] Initing router for ' + routeName);
    // Initialize the route to add its functionality to router
    require('./' + routeName)(router);
    
    // Add router to the speficied route name in the app
    app.use('/' + changeCase.paramCase(routeName), router);
    logger.info('[ROUTES] Inited under API call:' + ('/' + changeCase.paramCase(routeName)));
  }); 
};