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
        parser.add_argument('appVersion', required=True)
        parser.add_argument('clientLanguage')
        args = parser.parse_args()
        fbc = FirebaseCon(args['X-idToken'])

        mysqlCon.insertQuery('feedback', [{
            'userId': fbc.uid,
            'appVersion': args['appVersion'],
            'liked': args['liked'],
            'suggestion': None,
            'submitTime': datetime.now(),
            'clientLanguage': args['clientLanguage'],
            'deviceModel': args['deviceModel'],
            'devicePlatform': args['devicePlatform'],
            'deviceVersion': args['deviceVersion'],
        }], updateOnDuplicate=True)

        mysqlCon.db.commit()

        return {}, 201

    def put(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('appVersion', required=True)
        parser.add_argument('suggestion')
        args = parser.parse_args()
        fbc = FirebaseCon(args['X-idToken'])

        mysqlCon.wQuery(
            'UPDATE feedback SET suggestion = %s WHERE userId = %s AND appVersion = %s',
            (args['suggestion'], fbc.uid, args['appVersion'])
        )

        mysqlCon.db.commit()

        return {}

    def get(self):
        # client should decide is it time to ask for feedback, then call this to check if user already give feedback for this version
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('appVersion', required=True)
        args = parser.parse_args()
        fbc = FirebaseCon(args['X-idToken'])

        feedback = mysqlCon.rQuery(
            'SELECT appVersion FROM feedback WHERE userId = %s AND appVersion = %s',
            (fbc.uid, args['appVersion'])
        )

        return len(feedback) > 0
