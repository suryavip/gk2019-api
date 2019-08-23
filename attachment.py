from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from rules import Rules
import uuid
import werkzeug
from datetime import datetime


class TempAttachment(Resource):
    def post(self):
        # upload to temporary
        # directory is temp_attachment/{yyyy-mm-dd}/{uid}/
        # mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        '''parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')'''
        parser.add_argument('file', required=True, type=werkzeug.datastructures.FileStorage, location='files')
        args = parser.parse_args()

        #fbc = FirebaseCon(args['X-idToken'])

        f = args['file']

        # f.save('temp_attachment/{}/{}/{}'.format(datetime.now().strftime('%Y-%m-%d'), 'uid', uuid.uuid4()))
        f.save('{}'.format(uuid.uuid4()))

        return {
            'hello': 'world',
            'content_length': f.content_length,
            'content_type': f.content_type,
            'mimetype': f.mimetype,
            'mimetype_params': f.mimetype_params,
        }, 201
