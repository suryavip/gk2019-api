from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup, GroupsOfUser
from sendNotification import SendNotification
from group import Group
from rules import Rules
from util import getGroupName
import uuid


class Member(Resource):
    def post(self, gid):  # stranger sending request
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        # check for group joined limit
        gou = GroupsOfUser(fbc.uid)
        if len(gou.all) >= Rules.maxGroupPerUser:
            abort(400, code='cannot join more than {} groups'.format(Rules.maxGroupPerUser))

        # check for members joined limit
        mog = MembersOfGroup(gid, fbc.uid)
        if mog.rStatus != '':
            abort(400, code='already in group')
        if len(mog.insider) >= Rules.maxUserPerGroup:
            abort(400, code='group is full')

        # store data
        mysqlCon.insertQuery('memberdata', [{
            'groupId': gid,
            'userId': fbc.uid,
            'level': 'pending',
        }])

        # send notif to admins
        SendNotification(
            mog.byLevel['admin'],
            'pending-new',
            data={
                'groupId': gid,
                'groupName': getGroupName(mysqlCon, gid),
                'performerUserId': fbc.uid,
                'performerName': fbc.decoded_token['name'],
            },
            tag='pending-new-{}'.format(gid),
        )

        # poke admins to update member
        # poke requester to update group
        rdbPathUpdate = ['poke/{}/member/{}'.format(u, gid) for u in mog.byLevel['admin']]
        rdbPathUpdate.append('poke/{}/group'.format(fbc.uid))
        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return Group().get(), 201  # update requester's group channel. no need to update requester member channel, because there will be no update since memberdata only given to insider

    def put(self, gid):  # accept pending, promote member, demote admin
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('userId', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])
        target = fbc.uid if args['userId'] == None else args['userId']

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
            SendNotification(
                [target],
                'member-new-target',
                data=notifData,
                tag='member-new-target-{}'.format(gid),
            )
            notifData['targetUserId'] = target
            notifData['targetName'] = mog.tName
            SendNotification(
                notifTarget,
                'member-new',
                data=notifData,
                tag='member-new-{}'.format(gid),
            )
        elif mog.tStatus == 'member':
            # set to admin. send to target and "insider except target and self"
            SendNotification(
                [target],
                'admin-new-target',
                data=notifData,
                tag='admin-new-target-{}'.format(gid),
            )
            notifData['targetUserId'] = target
            notifData['targetName'] = mog.tName
            SendNotification(
                notifTarget,
                'admin-new',
                data=notifData,
                tag='admin-new-{}'.format(gid),
            )
        elif mog.tStatus == 'admin':
            # admin demote himself. send to "insider except target and self"
            SendNotification(
                notifTarget,
                'admin-stop',
                data=notifData,
                tag='admin-stop-{}'.format(gid),
            )

        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(gid)

    def delete(self, gid):  # cancel pending, delete member or delete admin
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('userId', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])
        target = fbc.uid if args['userId'] == None else args['userId']

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

        rdbPathUpdate = ['poke/{}/group'.format(target)]

        # modify data
        if mog.tStatus == 'admin' and len(mog.insider) == 1:  # the only left. destroy this group
            mysqlCon.wQuery('DELETE FROM groupdata WHERE groupId = %s', (gid,))
            mysqlCon.wQuery('UPDATE attachmentdata SET deleted = 1 WHERE ownerGroupId = %s', (gid,))
            # pending should get poked since pending wont be in part of equation of insider == 1
            rdbPathUpdate += ['poke/{}/group'.format(u) for u in mog.byLevel['pending']]
        else:
            mysqlCon.wQuery(
                'DELETE FROM memberdata WHERE groupId = %s AND userId = %s',
                (gid, target)
            )
            if mog.tStatus == 'pending': 
                # update only admin since only admin get updated when this pending send request
                rdbPathUpdate += ['poke/{}/member/{}'.format(u, gid) for u in mog.byLevel['admin']]
            else:
                rdbPathUpdate += ['poke/{}/member/{}'.format(u, gid) for u in mog.exclude(mog.insider, [target])]

        notifData = {
            'groupId': gid,
            'groupName': getGroupName(mysqlCon, gid),
            'performerUserId': fbc.uid,
            'performerName': fbc.decoded_token['name'],
        }
        notifTarget = mog.exclude(mog.insider, [fbc.uid, target])
        if mog.tStatus == 'member' and target == fbc.uid:
            # leave. send notif to insider except self
            SendNotification(
                notifTarget,
                'member-delete-self',
                data=notifData,
                tag='member-delete-self-{}'.format(gid),
            )
        elif mog.tStatus == 'member':
            # kick member. send notif to insider except self and target
            notifData['targetUserId'] = target
            notifData['targetName'] = mog.tName
            SendNotification(
                notifTarget,
                'member-delete',
                data=notifData,
                tag='member-delete-{}'.format(gid),
            )
        elif mog.tStatus == 'admin':
            # admin leave. send notif to insider except self
            SendNotification(
                notifTarget,
                'admin-delete',
                data=notifData,
                tag='admin-delete-{}'.format(gid),
            )

        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(gid)

    def get(self, gid):
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        mog = MembersOfGroup(gid, fbc.uid)
        if mog.rStatus != 'admin' and mog.rStatus != 'member':
            abort(404, code='requester is not insider')

        result = []
        for i in mog.all:
            if mog.rStatus == 'member' and i['level'] == 'pending':
                continue
            result.append({
                'userId': i['userId'],
                'level': i['level'],
            })

        return result
