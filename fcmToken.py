from flask_restful import Resource, reqparse

from connection import FirebaseCon, MysqlCon

from sendNotification import SendNotification

from datetime import datetime


class FCMToken(Resource):
    def post(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('new', required=True, help='new')
        parser.add_argument('old', required=True, help='old')
        parser.add_argument('deviceModel')
        parser.add_argument('devicePlatform')
        parser.add_argument('deviceVersion')
        parser.add_argument('appVersion')
        parser.add_argument('clientLanguage')
        args = parser.parse_args()
        fbc = FirebaseCon(args['X-idToken'])

        mysqlCon.insertQuery('fcmtoken', [{
            'fcmToken': args['new'],
            'userId': fbc.uid,
            'deviceModel': args['deviceModel'],
            'devicePlatform': args['devicePlatform'],
            'deviceVersion': args['deviceVersion'],
            'appVersion': args['appVersion'],
            'clientLanguage': args['clientLanguage'],
            'lastReported': datetime.now(),
        }], updateOnDuplicate=True)

        if args['old'] != '':
            mysqlCon.wQuery("DELETE FROM fcmtoken WHERE fcmToken = %s", (args['old'],))

        mysqlCon.db.commit()

        return {}, 201

    def delete(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('old', required=True, help='old')
        args = parser.parse_args()

        mysqlCon.wQuery("DELETE FROM fcmtoken WHERE fcmToken = %s", (args['old'],))

        mysqlCon.db.commit()

        return {}

    def get(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()
        fbc = FirebaseCon(args['X-idToken'])

        # send notif to target
        SendNotification(
            [fbc.uid],
            'test',
        )

        mysqlCon.db.commit()

        return {}
