var ERR = require('async-stacktrace');
var express = require('express');
var router = express.Router();

const path = require('path');
const debug = require('debug')('prairielearn:' + path.basename(__filename, '.js'));

var error = require('@prairielearn/prairielib/error');
var sqldb = require('@prairielearn/prairielib/sql-db');
var sqlLoader = require('@prairielearn/prairielib/sql-loader');

var sql = sqlLoader.loadSqlEquiv(__filename);

router.get('/', function(req, res, next) {
    sqldb.query(sql.select_course_users, {course_id: res.locals.course.id}, function(err, result) {
        if (ERR(err, next)) return;
        debug(result.rows);
        res.locals.course_users = result.rows;
        res.render(__filename.replace(/\.js$/, '.ejs'), res.locals);
    });
});

router.post('/', function(req, res, next) {
    if (!res.locals.authz_data.has_course_permission_own) return next(new Error('Insufficient permissions'));
    if (req.body.__action == 'course_permissions_insert_by_user_uid') {
        let params = [
            res.locals.course.id,
            req.body.uid,
            req.body.course_role,
            res.locals.authz_data.authn_user.user_id,
        ];
        sqldb.call('course_permissions_insert_by_user_uid', params, function(err, _result) {
            if (ERR(err, next)) return;
            res.redirect(req.originalUrl);
        });
    } else if (req.body.__action == 'course_permissions_update_role') {
        let params = [
            res.locals.course.id,
            req.body.user_id,
            req.body.course_role,
            res.locals.authz_data.authn_user.user_id,
        ];
        sqldb.call('course_permissions_update_role', params, function(err, _result) {
            if (ERR(err, next)) return;
            res.redirect(req.originalUrl);
        });
    } else if (req.body.__action == 'course_permissions_delete') {
        var params = [
            res.locals.course.id,
            req.body.user_id,
            res.locals.authz_data.authn_user.user_id,
        ];
        sqldb.call('course_permissions_delete', params, function(err, _result) {
            if (ERR(err, next)) return;
            res.redirect(req.originalUrl);
        });
    } else {
        return next(error.make(400, 'unknown __action', {locals: res.locals, body: req.body}));
    }
});

module.exports = router;
