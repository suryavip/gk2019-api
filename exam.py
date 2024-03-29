from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup
from sendNotification import SendNotification
from util import getGroupName, getSingleField, verifyDate, verifyTime, validateAttachment, updateAttachment
from datetime import datetime
import uuid


class Exam(Resource):
    def getSubject(self, mysqlCon, eid):
        return getSingleField(mysqlCon, 'subject', 'examdata', 'examId', eid)

    def post(self, owner):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('examId', default='')
        parser.add_argument('subject', required=True, help='subject')
        parser.add_argument('examDate', required=True, help='examDate')
        parser.add_argument('examTime', default=None)
        parser.add_argument('note', default=None)
        parser.add_argument('attachment', default=[], action='append', type=dict)
        args = parser.parse_args()

        if len(args['subject']) < 1:
            abort(400, code='subject is required')
        if verifyDate(args['examDate']) != True:
            abort(400, code='invalid examDate format')
        if args['examTime'] != None and verifyTime(args['examTime']) != True:
            abort(400, code='invalid examTime format')
        if validateAttachment(args['attachment']) != True:
            abort(400, code='invalid attachments')

        fbc = FirebaseCon(args['X-idToken'])

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
            eid = str(uuid.uuid4())
        else:
            ownerCol = 'ownerUserId'
            eid = str(uuid.uuid4()) if args['examId'] == '' else args['examId']

        # store data
        mysqlCon.insertQuery('examdata', [{
            'examId': eid,
            ownerCol: owner,
            'subject': args['subject'],
            'examDate': args['examDate'],
            'examTime': args['examTime'],
            'note': args['note'],
        }])

        # store attachments
        updateAttachment(mysqlCon, args['attachment'], ownerCol, owner, 'examId', eid)

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            SendNotification(
                mog.exclude(mog.insider, [fbc.uid]),
                'exam-new',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                    'examId': eid,
                    'subject': args['subject'],
                },
                tag='exam-{}'.format(eid),
            )
            rdbPathUpdate = ['poke/{}/exam/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/exam/{}'.format(fbc.uid, owner))

        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(owner), 201

    def put(self, owner):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('examId', required=True, help='examId')
        parser.add_argument('examDate', required=True, help='examDate')
        parser.add_argument('examTime', default=None)
        parser.add_argument('note', default=None)
        parser.add_argument('attachment', default=[], action='append', type=dict)
        args = parser.parse_args()

        if verifyDate(args['examDate']) != True:
            abort(400, code='invalid examDate format')
        if args['examTime'] != None and verifyTime(args['examTime']) != True:
            abort(400, code='invalid examTime format')
        if validateAttachment(args['attachment']) != True:
            abort(400, code='invalid attachments')

        fbc = FirebaseCon(args['X-idToken'])

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
        else:
            ownerCol = 'ownerUserId'

        eid = args['examId']

        # store data
        mysqlCon.wQuery(
            'UPDATE examdata SET examDate = %s, examTime = %s, note = %s WHERE examId = %s AND {} = %s'.format(ownerCol),
            (args['examDate'], args['examTime'], args['note'], eid, owner)
        )
        changed = mysqlCon.cursor.rowcount > 0

        # update attachments
        changed2 = updateAttachment(mysqlCon, args['attachment'], ownerCol, owner, 'examId', eid)

        if changed == False and changed2 == False:
            return self.get(owner)

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            SendNotification(
                mog.exclude(mog.insider, [fbc.uid]),
                'exam-edit',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                    'examId': eid,
                    'subject': self.getSubject(mysqlCon, eid),
                },
                tag='exam-{}'.format(eid),
            )
            rdbPathUpdate = ['poke/{}/exam/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/exam/{}'.format(fbc.uid, owner))

        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(owner)

    def delete(self, owner):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('examId', required=True, help='examId')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        eid = args['examId']

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
            subject = self.getSubject(mysqlCon, eid)
        else:
            ownerCol = 'ownerUserId'

        # store data
        mysqlCon.wQuery(
            'DELETE FROM examdata WHERE examId = %s AND {} = %s'.format(ownerCol),
            (args['examId'], owner)
        )

        # delete attachment
        updateAttachment(mysqlCon, [], ownerCol, owner, 'examId', eid)

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            SendNotification(
                mog.exclude(mog.insider, [fbc.uid]),
                'exam-delete',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                    'examId': eid,
                    'subject': subject,
                },
                tag='exam-{}'.format(eid),
            )
            rdbPathUpdate = ['poke/{}/exam/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/exam/{}'.format(fbc.uid, owner))

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

        exam = mysqlCon.rQuery(
            'SELECT examId, subject, examDate, examTime, note FROM examdata WHERE {} = %s'.format(ownerCol),
            (owner,)
        )

        preResult = {}
        for (examId, subject, examDate, examTime, note) in exam:
            eTime = None
            if examTime != None:
                eTime = (datetime.min + examTime).time().isoformat(timespec='minutes')
            preResult[examId] = {
                'examId': examId,
                'subject': subject,
                'examDate': examDate.isoformat(),
                'examTime': eTime,
                'note': note,
                'attachment': [],
            }

        if len(preResult.keys()) > 0:
            q = ['%s'] * len(preResult.keys())
            q = ','.join(q)
            attachment = mysqlCon.rQuery(
                'SELECT attachmentId, originalFilename, examId FROM attachmentdata WHERE examId IN ({}) AND deleted = 0'.format(q),
                tuple(preResult.keys())
            )

            for (attachmentId, originalFilename, examId) in attachment:
                preResult[examId]['attachment'].append({
                    'attachmentId': attachmentId,
                    'originalFilename': originalFilename,
                })

        result = [preResult[examId] for examId in preResult]

        return {
            'channel': 'exam/{}'.format(owner),
            'data': result,
        }
