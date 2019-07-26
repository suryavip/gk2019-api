from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup, GroupsOfUser
from notification import Notification
from group import Group
from rules import Rules
from util import getGroupName, verifyDate
import uuid


class Assignment(Resource):
    def post(self, owner):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('subject', required=True, help='subject')
        parser.add_argument('date', required=True, help='date')
        parser.add_argument('note', default=None, help='note')
        args = parser.parse_args()
        
        if len(args['subject']) < 1:
            abort(400, code='subject is required')
        if verifyDate(args['date']) != True:
            abort(400, code='invalid date format')

        fbc = FirebaseCon(args['X-idToken'])

        # check for valid privilege
        mog = MembersOfGroup(owner, fbc.uid)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
        else:
            ownerCol = 'ownerUserId'

        aid = uuid.uuid4()

        # store data
        mysqlCon.insertQuery('assignmentdata', [{
            'assignmentId': aid,
            ownerCol: owner,
            'subject': args['subject'],
            'dueDate': args['date'],
            'note': args['note'],
        }])

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            Notification(
                mog.exclude(mog.insider, [fbc.uid]),
                'assignment-new',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                },
                tag='assignment-new-{}'.format(owner),
            )
            rdbPathUpdate = ['poke/{}/assignment/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/assignment/{}'.format(fbc.uid, owner))

        fbc.updateRDBTimestamp(rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(owner), 201

    def put(self, gid):  # accept pending, promote member, demote admin
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('userId', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])
        target = fbc.uid if 'userId' not in args else args['userId']

        # check privilege
        mog = MembersOfGroup(gid, fbc.uid, target, True)
        expectedRequester = []
        if mog.tStatus == 'pending' or mog.tStatus == 'member':
            expectedRequester = mog.byLevel['admin']  # admin can accept pending and promote member
        elif mog.tStatus == 'admin':
            expectedRequester = [target]  # only target himself who can demote from admin

        if fbc.uid not in expectedRequester:
            abort(400, code='requester not have right privilege')

        nextLevel = {
            'pending': 'member',
            'member': 'admin',
            'admin': 'member',
        }[mog.tStatus]

        mysqlCon.wQuery(
            'UPDATE memberdata SET level = %s WHERE groupId = %s AND userId = %s',
            (nextLevel, gid, target)
        )

        rdbPathUpdate = ['poke/{}/group'.format(u) for u in mog.insider]
        rdbPathUpdate += ['poke/{}/member/{}'.format(u, gid) for u in mog.insider]
        if mog.tStatus == 'pending':
            rdbPathUpdate.append('poke/{}/group'.format(target))
            rdbPathUpdate.append('poke/{}/member/{}'.format(target, gid))

        # sending notif
        notifData = {
            'groupId': gid,
            'groupName': getGroupName(mysqlCon, gid),
            'performerUserId': fbc.uid,
            'performerName': fbc.decoded_token['name'],
        }
        notifTarget = mog.exclude(mog.insider, [fbc.uid, target])
        if mog.tStatus == 'pending':
            # accepted to group. send to target and "insider except target and self"
            Notification(
                [target],
                'member-new-target',
                data=notifData,
                tag='member-new-target-{}'.format(gid),
            )
            notifData['targetUserId'] = target
            notifData['targetName'] = mog.tName
            Notification(
                notifTarget,
                'member-new',
                data=notifData,
                tag='member-new-{}'.format(gid),
            )
        elif mog.tStatus == 'member':
            # set to admin. send to target and "insider except target and self"
            Notification(
                [target],
                'admin-new-target',
                data=notifData,
                tag='admin-new-target-{}'.format(gid),
            )
            notifData['targetUserId'] = target
            notifData['targetName'] = mog.tName
            Notification(
                notifTarget,
                'admin-new',
                data=notifData,
                tag='admin-new-{}'.format(gid),
            )
        elif mog.tStatus == 'admin':
            # admin demote himself. send to "insider except target and self"
            Notification(
                notifTarget,
                'admin-stop',
                data=notifData,
                tag='admin-stop-{}'.format(gid),
            )

        fbc.updateRDBTimestamp(rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(gid)

    def delete(self, gid):  # cancel pending, delete member or delete admin
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('userId', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])
        target = fbc.uid if 'userId' not in args else args['userId']

        # check privilege
        mog = MembersOfGroup(gid, fbc.uid, target, True)
        expectedRequester = []
        if mog.tStatus == 'pending' or mog.tStatus == 'member':
            expectedRequester = [target] + mog.byLevel['admin']  # admin can delete pending and member too
        elif mog.tStatus == 'admin':
            expectedRequester = [target]  # only himself who can delete admin

        if fbc.uid not in expectedRequester:
            abort(400, code='requester not have right privilege')
        if mog.tStatus == 'admin' and len(mog.byLevel['admin']) < 2 and len(mog.byLevel['member']) > 0:
            abort(400, code='must set another admin first if there is another member (non admin)')

        rdbPathUpdate = []

        # modify data
        if mog.tStatus == 'admin' and len(mog.insider) == 1:  # the only left. destroy this group
            mysqlCon.wQuery('DELETE FROM groupdata WHERE groupId = %s', (gid,))
            rdbPathUpdate.append('poke/{}/group'.format(target))
            rdbPathUpdate.append('poke/{}/member/{}'.format(target, gid))
            # pending should get poked since pending wont be in part of equation of insider == 1
            rdbPathUpdate += ['poke/{}/group'.format(u) for u in mog.byLevel['pending']]
        else:
            mysqlCon.wQuery(
                'DELETE FROM memberdata WHERE groupId = %s AND userId = %s',
                (gid, target)
            )
            if mog.tStatus == 'pending':  # so rejected user will update his group data channel
                rdbPathUpdate.append('poke/{}/group'.format(target))
                # update only admin since only admin get updated when this pending send request
                rdbPathUpdate += ['poke/{}/member/{}'.format(u, gid) for u in mog.byLevel['admin']]
            else:
                rdbPathUpdate += ['poke/{}/member/{}'.format(u, gid) for u in mog.insider]

        notifData = {
            'groupId': gid,
            'groupName': getGroupName(mysqlCon, gid),
            'performerUserId': fbc.uid,
            'performerName': fbc.decoded_token['name'],
        }
        notifTarget = mog.exclude(mog.insider, [fbc.uid, target])
        if mog.tStatus == 'member' and target == fbc.uid:
            # leave. send notif to insider except self
            Notification(
                notifTarget,
                'member-delete-self',
                data=notifData,
                tag='member-delete-self-{}'.format(gid),
            )
        elif mog.tStatus == 'member':
            # kick member. send notif to insider except self and target
            notifData['targetUserId'] = target
            notifData['targetName'] = mog.tName
            Notification(
                notifTarget,
                'member-delete',
                data=notifData,
                tag='member-delete-{}'.format(gid),
            )
        elif mog.tStatus == 'admin':
            # admin leave. send notif to insider except self
            Notification(
                notifTarget,
                'admin-delete',
                data=notifData,
                tag='admin-delete-{}'.format(gid),
            )

        fbc.updateRDBTimestamp(rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(gid)

    def get(self, gid):
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        mog = MembersOfGroup(gid, fbc.uid)
        if mog.rStatus != 'admin' and mog.rStatus != 'member':
            abort(400, code='requester is not insider')

        result = {}
        for i in mog.all:
            if mog.rStatus == 'member' and i.level == 'pending':
                continue
            result[i.userId] = i.level

        return result
