from flask_restful import Resource, reqparse

from connection import FirebaseCon, MysqlCon

from datetime import datetime


class Feedback(Resource):
    def post(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('liked', type=bool ,required=True, help='liked')
        parser.add_argument('deviceModel')
        parser.add_argument('devicePlatform')
        parser.add_argument('deviceVersion')
        parser.add_argument('appVersion')
        parser.add_argument('clientLanguage')
        args = parser.parse_args()
        fbc = FirebaseCon(args['X-idToken'])

        mysqlCon.insertQuery('feedback', [{
            'userId': fbc.uid,
            'liked': args['liked'],
            'submitTime': datetime.now(),
            'clientLanguage': args['clientLanguage'],
            'deviceModel': args['deviceModel'],
            'devicePlatform': args['devicePlatform'],
            'deviceVersion': args['deviceVersion'],
            'appVersion': args['appVersion'],
        }])

        mysqlCon.db.commit()

        return {}, 201

    def put(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('suggestion')
        args = parser.parse_args()
        fbc = FirebaseCon(args['X-idToken'])

        mysqlCon.wQuery(
            'UPDATE groupdata SET name = %s, school = %s WHERE groupId = %s',
            (args['suggestion'], fbc.uid)
        )

        mysqlCon.db.commit()

        return {}
