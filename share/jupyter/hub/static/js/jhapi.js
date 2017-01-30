// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

define(['jquery', 'utils'], function ($, utils) {
    "use strict";

    var JHAPI = function (base_url) {
        this.base_url = base_url;
    };

    var default_options = {
        type: 'GET',
        contentType: "application/json",
        cache: false,
        dataType : "json",
        processData: false,
        success: null,
        error: utils.ajax_error_dialog,
    };

    var update = function (d1, d2) {
        $.map(d2, function (i, key) {
            d1[key] = d2[key];
        });
        return d1;
    };

    var ajax_defaults = function (options) {
        var d = {};
        update(d, default_options);
        update(d, options);
        return d;
    };

    JHAPI.prototype.api_request = function (path, options) {
        options = options || {};
        options = ajax_defaults(options || {});
        var url = utils.url_path_join(
            this.base_url,
            'api',
            utils.encode_uri_components(path)
        );
        $.ajax(url, options);
    };

    JHAPI.prototype.start_server = function (user, options) {
        options = options || {};
        options = update(options, {type: 'POST', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'server'),
            options
        );
    };

    JHAPI.prototype.stop_server = function (user, options) {
        options = options || {};
        options = update(options, {type: 'DELETE', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'server'),
            options
        );
    };

    JHAPI.prototype.list_users = function (options) {
        this.api_request('users', options);
    };

    JHAPI.prototype.get_user = function (user, options) {
        this.api_request(
            utils.url_path_join('users', user),
            options
        );
    };

    JHAPI.prototype.add_users = function (usernames, userinfo, options) {
        options = options || {};
        var data = update(userinfo, {usernames: usernames});
        options = update(options, {
            type: 'POST',
            dataType: null,
            data: JSON.stringify(data)
        });

        this.api_request('users', options);
    };

    JHAPI.prototype.edit_user = function (user, userinfo, options) {
        options = options || {};
        options = update(options, {
            type: 'PATCH',
            dataType: null,
            data: JSON.stringify(userinfo)
        });

        this.api_request(
            utils.url_path_join('users', user),
            options
        );
    };

    JHAPI.prototype.admin_access = function (user, options) {
        options = options || {};
        options = update(options, {
            type: 'POST',
            dataType: null,
        });

        this.api_request(
            utils.url_path_join('users', user, 'admin-access'),
            options
        );
    };

    JHAPI.prototype.delete_user = function (user, options) {
        options = options || {};
        options = update(options, {type: 'DELETE', dataType: null});
        this.api_request(
            utils.url_path_join('users', user),
            options
        );
    };

    JHAPI.prototype.shutdown_hub = function (data, options) {
        options = options || {};
        options = update(options, {type: 'POST'});
        if (data) {
            options.data = JSON.stringify(data);
        }
        this.api_request('shutdown', options);
    };

    JHAPI.prototype.start_loopback = function (user, options) {
        options = options || {};
        options = update(options, {type: 'POST', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'loopback'),
            options
        );
    };

    JHAPI.prototype.stop_loopback = function (user, options) {
        options = options || {};
        options = update(options, {type: 'DELETE', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'loopback'),
            options
        );
    };

    JHAPI.prototype.setup_loopback = function (user,apiInfo,options) {
        options = options || {};
        options = update(options, {type: 'PUT', dataType: null, data: apiInfo});
        console.log('options:'+JSON.stringify(options));
        this.api_request(
            utils.url_path_join('users', user, 'loopback'),
            options
        );
    };

    JHAPI.prototype.get_loopback_status = function (user, options) {
        options = options || {};
        options = update(options, {type: 'GET', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'loopback'),
            options
        );
    };

    JHAPI.prototype.get_blog_status = function (user, options) {
        options = options || {};
        options = update(options, {type: 'GET', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'wordpress'),
            options
        );
    };

    JHAPI.prototype.get_fieldtrip_status = function (user, options) {
        options = options || {};
        options = update(options, {type: 'GET', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'fieldtrip'),
            options
        );
    };

    JHAPI.prototype.get_loopback_credential = function (user, options) {
        options = options || {};
        options = update(options, {type: 'GET', dataType: null, data: 'credential=get'});
        this.api_request(
            utils.url_path_join('users', user, 'loopback'),
            options
        );
    };

    JHAPI.prototype.get_blog_credential = function (user, options) {
        options = options || {};
        options = update(options, {type: 'GET', dataType: null, data: 'credential=get'});
        this.api_request(
            utils.url_path_join('users', user, 'wordpress'),
            options
        );
    };


    JHAPI.prototype.start_mysql = function (user, options) {
        options = options || {};
        options = update(options, {type: 'POST', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'mysql'),
            options
        );
    };

    JHAPI.prototype.stop_mysql = function (user, options) {
        options = options || {};
        options = update(options, {type: 'DELETE', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'mysql'),
            options
        );
    };

    JHAPI.prototype.start_wordpress = function (user, options) {
        options = options || {};
        options = update(options, {type: 'POST', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'wordpress'),
            options
        );
    };

    JHAPI.prototype.stop_wordpress = function (user, options) {
        options = options || {};
        options = update(options, {type: 'DELETE', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'wordpress'),
            options
        );
    };

    JHAPI.prototype.start_fieldtrip = function (user, options) {
        options = options || {};
        options = update(options, {type: 'POST', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'fieldtrip'),
            options
        );
    };

    JHAPI.prototype.stop_fieldtrip = function (user, options) {
        options = options || {};
        options = update(options, {type: 'DELETE', dataType: null});
        this.api_request(
            utils.url_path_join('users', user, 'fieldtrip'),
            options
        );
    };


    return JHAPI;
});
