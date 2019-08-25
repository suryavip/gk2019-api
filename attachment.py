from flask import send_file
from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup
from rules import Rules
from util import saveUploadedFile
import uuid
import werkzeug


class TempAttachment(Resource):
    def post(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('file', required=True, type=werkzeug.datastructures.FileStorage, location='files')
        parser.add_argument('thumbnail', type=werkzeug.datastructures.FileStorage, location='files')
        parser.add_argument('originalFilename', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        attachmentId = str(uuid.uuid4())

        mysqlCon.insertQuery('attachmentdata', [{
            'attachmentId': attachmentId,
            'ownerUserId': fbc.uid,
            'originalFilename': args['originalFilename'],
        }])

        thumbSource = None
        if 'thumbnail' in args:
            thumbSource = args['thumbnail']

        upload = saveUploadedFile(
            args['file'],
            'storage/attachment/{}'.format(attachmentId),
            Rules.acceptedAttachmentType,
            Rules.maxAttachmentSize,
            thumbSource=thumbSource,
        )
        if isinstance(upload, str):
            abort(400, code=upload)

        mysqlCon.db.commit()

        return {
            'attachmentId': attachmentId,
        }, 201


class Attachment(Resource):
    def get(self, aid):
        # aid may ended with _thumb
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('r', required=True, location='args') # requester
        parser.add_argument('download', default=False, type=bool, location='args')
        args = parser.parse_args()

        target = 'storage/attachment/{}'.format(aid)

        if aid.endswith('_thumb'):
            aid.replace('_thumb', '')

        attachment = mysqlCon.rQuery(
            'SELECT ownerUserId, ownerGroupId, originalFilename FROM attachmentdata WHERE attachmentId = %s',
            (aid,)
        )
        if len(attachment) < 1:
            abort(404, code='attachment not found')

        owner = None
        originalFilename = None
        for (ownerUserId, ownerGroupId, fn) in attachment:
            owner = ownerUserId if ownerUserId == args['r'] else ownerGroupId
            originalFilename = fn

        if owner == None:
            abort(400, code='not owning this')

        # check for valid privilege
        mog = MembersOfGroup(owner, args['r'])
        if len(mog.all) > 0:
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')

        try:
            if args['download'] == True:
                return send_file(target, as_attachment=True, attachment_filename=originalFilename)

            return send_file(target)
        except:
            abort(404, code='not found')
