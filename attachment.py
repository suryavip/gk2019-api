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
        parser.add_argument('originalFilename', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        attachmentId = uuid.uuid4()

        mysqlCon.insertQuery('attachmentdata', [{
            'attachmentId': attachmentId,
            'ownerUserId': fbc.uid,
            'originalFilename': args['originalFilename'],
        }])

        f = args['file']

        if f.mimetype not in Rules.acceptedAttachmentType:
            abort(400, code='unknown type')

        dest = 'attachment/{}'.format(uuid.uuid4())
        f.save(dest)

        if os.stat(dest).st_size > Rules.maxAttachmentSize:
            os.remove(dest)
            abort(400, code='file size is too big')

        return {
            'attachmentId': attachmentId,
        }, 201


class Attachment(Resource):
    def get(self, aid):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        attachment = mysqlCon.rQuery(
            'SELECT ownerUserId, ownerGroupId, originalFilename FROM attachmentdata WHERE attachmentId = %s AND (assignmentId IS NOT NULL OR examId IS NOT NULL)',
            (aid,)
        )
        if len(attachment) < 1:
            abort(404, code='attachment not found')

        owner = None
        for (ownerUserId, ownerGroupId) in attachment:
            owner = ownerUserId if ownerUserId == fbc.uid else ownerGroupId

        if owner == None:
            abort(400, code='not owning this')

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')

        target = 'attachment/{}'.format(aid)

        return send_file(target)
