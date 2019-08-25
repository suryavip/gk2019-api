from flask import send_file
from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon
from rules import Rules
from util import saveUploadedFile
import werkzeug


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


class ProfilePic(Resource):
    def get(self, uid):
        parser = reqparse.RequestParser()
        parser.add_argument('idToken', required=True, help='a', location='args')
        parser.add_argument('thumb', default=False, type=bool, location='args')
        args = parser.parse_args()

        FirebaseCon(args['idToken'])

        target = 'storage/profile_pic/{}'.format(uid)
        if args['thumb'] == True:
            target = '{}_thumb'.format(target)

        return send_file(target)
