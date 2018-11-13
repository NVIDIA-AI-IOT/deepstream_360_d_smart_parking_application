var uiConfigModel = require('../models/ui_config_model');

module.exports = function (router) {
  'use strict';

  // This will handle the url calls for /ui-config
  router.route('/')
    .get(uiConfigModel.getUiConfig);
  };