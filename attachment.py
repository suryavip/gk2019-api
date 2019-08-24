from flask import send_file
from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup
from rules import Rules
import uuid
import werkzeug
import os


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

        f = args['file']
        if f.mimetype not in Rules.acceptedAttachmentType:
            abort(400, code='unknown type')

        fDest = 'storage/attachment/{}'.format(attachmentId)
        try:
            f.save(fDest)
        except:
            abort(500, code='failed to write')

        if os.stat(fDest).st_size > Rules.maxAttachmentSize:
            os.remove(fDest)
            abort(400, code='file size is too big')

        if 'thumbnail' in args:
            t = args['thumbnail']
            if t.mimetype not in Rules.acceptedAttachmentType:
                abort(400, code='unknown type')

            tDest = 'storage/attachment/{}_thumb'.format(attachmentId)
            try:
                t.save(tDest)
            except:
                os.remove(fDest)
                abort(500, code='failed to write')
                
            if os.stat(tDest).st_size > Rules.maxAttachmentSize:
                os.remove(fDest)
                os.remove(tDest)
                abort(400, code='file size is too big')

        mysqlCon.db.commit()

        return {
            'attachmentId': attachmentId,
        }, 201


class Attachment(Resource):
    def get(self, aid):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='args')
        parser.add_argument('download', default=False, type=bool, location='args')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        attachment = mysqlCon.rQuery(
            'SELECT ownerUserId, ownerGroupId, originalFilename FROM attachmentdata WHERE attachmentId = %s',
            (aid,)
        )
        if len(attachment) < 1:
            abort(404, code='attachment not found')

        owner = None
        originalFilename = None
        for (ownerUserId, ownerGroupId, fn) in attachment:
            owner = ownerUserId if ownerUserId == fbc.uid else ownerGroupId
            originalFilename = fn

        if owner == None:
            abort(400, code='not owning this')

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')

        target = 'storage/attachment/{}'.format(aid)

        if args['download'] == True:
            return send_file(target, as_attachment=True, attachment_filename=originalFilename)

        return send_file(target)
