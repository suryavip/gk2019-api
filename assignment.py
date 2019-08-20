from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup
from sendNotification import SendNotification
from util import getGroupName, getSingleField, verifyDate, validateAttachment, updateAttachment, moveFromTempAttachment
import uuid
from datetime import datetime


class Assignment(Resource):
    def getSubject(self, mysqlCon, aid):
        return getSingleField(mysqlCon, 'subject', 'assignmentdata', 'assignmentId', aid)

    def post(self, owner):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('assignmentId', default='')
        parser.add_argument('subject', required=True, help='subject')
        parser.add_argument('dueDate', required=True, help='dueDate')
        parser.add_argument('note', default=None)
        parser.add_argument('attachment', default=[], action='append', type=dict)
        parser.add_argument('attachmentUploadDate', default=None) # this is to prevent attachment uploaded on date A but this request is proceeded on date B
        args = parser.parse_args()

        if len(args['subject']) < 1:
            abort(400, code='subject is required')
        if verifyDate(args['dueDate']) != True:
            abort(400, code='invalid dueDate format')
        if validateAttachment(args['attachment']) != True:
            abort(400, code='invalid attachments')
        if verifyDate(args['attachmentUploadDate']) != True:
            args['attachmentUploadDate'] = datetime.utcnow().strftime('%Y-%m-%d')

        fbc = FirebaseCon(args['X-idToken'])

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
            aid = str(uuid.uuid4())
        else:
            ownerCol = 'ownerUserId'
            aid = str(uuid.uuid4()) if args['assignmentId'] == '' else args['assignmentId']

        # store data
        mysqlCon.insertQuery('assignmentdata', [{
            'assignmentId': aid,
            ownerCol: owner,
            'subject': args['subject'],
            'dueDate': args['dueDate'],
            'note': args['note'],
        }])

        # store attachments
        updateAttachment(mysqlCon, args['attachment'], ownerCol, owner, 'assignmentId', aid)
        moveFromTempAttachment(fbc, args['attachmentUploadDate'], args['attachment'], owner)

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            SendNotification(
                mog.exclude(mog.insider, [fbc.uid]),
                'assignment-new',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                    'assignmentId': aid,
                    'subject': args['subject'],
                },
                tag='assignment-{}'.format(aid),
            )
            rdbPathUpdate = ['poke/{}/assignment/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/assignment/{}'.format(fbc.uid, owner))

        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(owner), 201

    def put(self, owner):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('assignmentId', required=True, help='assignmentId')
        parser.add_argument('dueDate', required=True, help='dueDate')
        parser.add_argument('note', default=None)
        parser.add_argument('attachment', default=[], action='append', type=dict)
        parser.add_argument('attachmentUploadDate', default=None) # this is to prevent attachment uploaded on date A but this request is proceeded on date B
        args = parser.parse_args()

        if verifyDate(args['dueDate']) != True:
            abort(400, code='invalid dueDate format')
        if validateAttachment(args['attachment']) != True:
            abort(400, code='invalid attachments')
        if verifyDate(args['attachmentUploadDate']) != True:
            args['attachmentUploadDate'] = datetime.utcnow().strftime('%Y-%m-%d')

        fbc = FirebaseCon(args['X-idToken'])

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
        else:
            ownerCol = 'ownerUserId'

        aid = args['assignmentId']

        # store data
        mysqlCon.wQuery(
            'UPDATE assignmentdata SET dueDate = %s, note = %s WHERE assignmentId = %s AND {} = %s'.format(ownerCol),
            (args['dueDate'], args['note'], aid, owner)
        )
        count = mysqlCon.cursor.rowcount

        # update attachments
        updateAttachment(mysqlCon, args['attachment'], ownerCol, owner, 'assignmentId', aid)
        count += mysqlCon.cursor.rowcount
        moveFromTempAttachment(fbc, args['attachmentUploadDate'], args['attachment'], owner)

        if count < 1:
            return self.get(owner)

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            SendNotification(
                mog.exclude(mog.insider, [fbc.uid]),
                'assignment-edit',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                    'assignmentId': aid,
                    'subject': self.getSubject(mysqlCon, aid),
                },
                tag='assignment-{}'.format(aid),
            )
            rdbPathUpdate = ['poke/{}/assignment/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/assignment/{}'.format(fbc.uid, owner))

        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(owner)

    def delete(self, owner):  # cancel pending, delete member or delete admin
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('assignmentId', required=True, help='assignmentId')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        aid = args['assignmentId']

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
            subject = self.getSubject(mysqlCon, aid)
        else:
            ownerCol = 'ownerUserId'

        # store data
        mysqlCon.wQuery(
            'DELETE FROM assignmentdata WHERE assignmentId = %s AND {} = %s'.format(ownerCol),
            (args['assignmentId'], owner)
        )

        # delete attachment
        updateAttachment(mysqlCon, [], ownerCol, owner, 'assignmentId', aid)

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            SendNotification(
                mog.exclude(mog.insider, [fbc.uid]),
                'assignment-delete',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                    'assignmentId': aid,
                    'subject': subject,
                },
                tag='assignment-{}'.format(aid),
            )
            rdbPathUpdate = ['poke/{}/assignment/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/assignment/{}'.format(fbc.uid, owner))

        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(owner)

    def get(self, owner):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
        else:
            ownerCol = 'ownerUserId'

        assignment = mysqlCon.rQuery(
            'SELECT assignmentId, subject, dueDate, note FROM assignmentdata WHERE {} = %s'.format(ownerCol),
            (owner,)
        )

        preResult = {}
        for (assignmentId, subject, dueDate, note) in assignment:
            preResult[assignmentId] = {
                'assignmentId': assignmentId,
                'subject': subject,
                'dueDate': dueDate.isoformat(),
                'note': note,
                'attachment': [],
            }

        if len(preResult.keys()) > 0:
            q = ['%s'] * len(preResult.keys())
            q = ','.join(q)
            attachment = mysqlCon.rQuery(
                'SELECT attachmentId, originalFilename, assignmentId FROM attachmentdata WHERE assignmentId IN ({})'.format(q),
                tuple(preResult.keys())
            )

            for (attachmentId, originalFilename, assignmentId) in attachment:
                preResult[assignmentId]['attachment'].append({
                    'attachmentId': attachmentId,
                    'originalFilename': originalFilename,
                })

        result = [preResult[assignmentId] for assignmentId in preResult]

        return result
