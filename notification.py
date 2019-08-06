from flask_restful import Resource, reqparse
from connection import FirebaseCon, MysqlCon
import json


class Notification(Resource):
    def get(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        notif = mysqlCon.rQuery(
            'SELECT notificationType, notificationTime, notificationData FROM notificationdata WHERE targetUserId = %s',
            (fbc.uid,)
        )
        result = [{
            'type': notifType,
            'time': notifTime.timestamp(),
            'data': json.loads(notifData),
        } for (notifType, notifTime, notifData) in notif]

        return result
