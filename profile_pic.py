from flask import send_file
from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from rules import Rules
from util import saveUploadedFile, getSingleField
import werkzeug
import os


class SelfProfilePic(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('file', required=True, type=werkzeug.datastructures.FileStorage, location='files')
        parser.add_argument('thumbnail', required=True, type=werkzeug.datastructures.FileStorage, location='files')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        upload = saveUploadedFile(
            args['file'],
            'storage/profile_pic/{}'.format(fbc.uid),
            Rules.profilePicType,
            Rules.maxProfilePicSize,
            thumbSource=args['thumbnail'],
        )
        if isinstance(upload, str):
            abort(400, code=upload)

        return {}, 201

    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        try:
            os.remove('storage/profile_pic/{}'.format(fbc.uid))
        except:
            pass
        try:
            os.remove('storage/profile_pic/{}_thumb'.format(fbc.uid))
        except:
            pass
            
        return {}


class ProfilePic(Resource):
    def get(self, uid):
        # uid may ended with _thumb
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('r', required=True, help='r', location='args')  # requester
        args = parser.parse_args()

        requester = getSingleField(mysqlCon, 'userId', 'userdata', 'userId', args['r'], default=None)
        if requester == None:
            abort(404, code='not authorized')

        target = 'storage/profile_pic/{}'.format(uid)
        try:
            return send_file(target)
        except:
            abort(404, code='not found')
