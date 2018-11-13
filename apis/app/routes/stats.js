var statsModel = require('../models/stats_model');

module.exports = function (router) {
  'use strict';

  // This will handle the url calls for /stats/:garageId
  router.route('/:garageId')
    .get(statsModel.getStats)
    .post(statsModel.getStats)
    ;
};