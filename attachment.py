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
        parser.add_argument('thumbnail', default=None, type=werkzeug.datastructures.FileStorage, location='files')
        parser.add_argument('originalFilename', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        attachmentId = str(uuid.uuid4())

        if isinstance(args['thumbnail'], werkzeug.datastructures.FileStorage):
            # image uploaded
            args['originalFilename'] = None
            acceptedType = Rules.acceptedAttachmentImageType

        elif isinstance(args['originalFilename'], str):
            # file uploaded
            args['thumbnail'] = None
            acceptedType = Rules.acceptedAttachmentFileType

        else:
            # no thumbnail no filename. reject because image must have thumbnail and file must have filename
            abort(400, code='thumbnail or originalFilename must be provided')

        mysqlCon.insertQuery('attachmentdata', [{
            'attachmentId': attachmentId,
            'ownerUserId': fbc.uid,
            'originalFilename': args['originalFilename'],
        }])

        upload = saveUploadedFile(
            args['file'],
            'storage/attachment/{}'.format(attachmentId),
            acceptedType,
            Rules.maxAttachmentSize,
            thumbSource=args['thumbnail'],
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
            aid = aid.replace('_thumb', '')

        attachment = mysqlCon.rQuery(
            'SELECT ownerUserId, ownerGroupId, originalFilename FROM attachmentdata WHERE attachmentId = %s',
            (aid,)
        )
        if len(attachment) < 1:
            abort(404, code='attachment not found')

        owner = None
        originalFilename = '{}.jpg'.format(aid) # so image download will have extension and name
        for (ownerUserId, ownerGroupId, fn) in attachment:
            owner = ownerUserId if ownerUserId == args['r'] else ownerGroupId
            if fn != None:
                originalFilename = fn

        if owner == None:
            abort(404, code='not owning this')

        # check for valid privilege
        mog = MembersOfGroup(owner, args['r'])
        if len(mog.all) > 0:
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(404, code='requester is not in group')

        try:
            if args['download'] == True:
                return send_file(target, as_attachment=True, attachment_filename=originalFilename)

            return send_file(target)
        except:
            abort(404, code='not found')
