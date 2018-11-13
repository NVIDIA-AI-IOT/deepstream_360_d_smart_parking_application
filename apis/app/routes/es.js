var esModel = require('../models/es_model');

module.exports = function (router) {
  'use strict';

  // This will handle the url calls for /es/events-deprecated 
  router.route('/events-deprecated')
    .get(esModel.searchEventsDeprecated)
    .post(esModel.searchEventsDeprecated)
    ;    
  
  // This will handle the url calls for /es/alerts  
  router.route('/alerts')
    .get(esModel.searchAnomaly)
    .post(esModel.searchAnomaly)
    ; 
    
  // This will handle the url calls for /es/events 
  router.route('/events')
    .get(esModel.searchEvents)
    .post(esModel.searchEvents)
    ;

};