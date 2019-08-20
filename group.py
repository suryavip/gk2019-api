from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup, GroupsOfUser
from sendNotification import SendNotification
from rules import Rules
from util import getGroupName
import uuid


class Group(Resource):
    def post(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('name', required=True, help='name')
        parser.add_argument('school', default=None)
        args = parser.parse_args()

        if len(args['name']) < 1:
            abort(400, code='name is required')

        fbc = FirebaseCon(args['X-idToken'])

        # check for group joined limit
        gou = GroupsOfUser(fbc.uid)
        if len(gou.all) >= Rules.maxGroupPerUser:
            abort(400, code='cannot join more than {} groups'.format(Rules.maxGroupPerUser))

        gid = str(uuid.uuid4())

        mysqlCon.insertQuery('groupdata', [{
            'groupId': gid,
            'name': args['name'],
            'school': args['school'],
        }])
        mysqlCon.insertQuery('memberdata', [{
            'groupId': gid,
            'userId': fbc.uid,
            'level': 'admin',
        }])

        rdbPathUpdate = ['poke/{}/group'.format(fbc.uid), 'poke/{}/member/{}'.format(fbc.uid, gid)]
        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(), 201

    def put(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('groupId', required=True, help='groupId')
        parser.add_argument('name', required=True, help='name')
        parser.add_argument('school', default=None)
        args = parser.parse_args()

        if len(args['name']) < 1:
            abort(400, code='name is required')

        fbc = FirebaseCon(args['X-idToken'])
        gid = args['groupId']

        # check privilege
        mog = MembersOfGroup(gid, fbc.uid)
        if mog.rStatus != 'admin' and mog.rStatus != 'member':
            abort(400, code='requester is not in group')

        mysqlCon.wQuery(
            'UPDATE groupdata SET name = %s, school = %s WHERE groupId = %s',
            (args['name'], args['school'], gid)
        )
        if mysqlCon.cursor.rowcount < 1:
            return self.get()

        # send notif to insider except self
        SendNotification(
            mog.exclude(mog.insider, [fbc.uid]),
            'group-edit',
            data={
                'groupId': gid,
                'groupName': getGroupName(mysqlCon, gid),
                'performerUserId': fbc.uid,
                'performerName': fbc.decoded_token['name'],
            },
            tag='group-edit-{}'.format(gid),
        )

        # poke everybody to update
        rdbPathUpdate = ['poke/{}/group'.format(u['userId']) for u in mog.all]
        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get()

    # there is no DELETE method because group will be deleted once there is no member/admin

    def get(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        group = mysqlCon.rQuery(
            'SELECT groupdata.groupId, name, school, level FROM groupdata JOIN memberdata ON groupdata.groupId = memberdata.groupId WHERE memberdata.userId = %s',
            (fbc.uid,)
        )
        result = [{
            'groupId': groupId,
            'name': name,
            'school': school,
            'level': level,
        } for (groupId, name, school, level) in group]

        groupById = {}
        for g in result:
            groupById[g['groupId']] = g['level']
        customToken = fbc.auth.create_custom_token(fbc.uid, {'groups': groupById})
        customToken = (customToken).decode()

        return {
            'groups': result,
            'customToken': customToken,
        }


class GroupInfo(Resource):

    def get(self, gid):
        mysqlCon = MysqlCon()
        group = mysqlCon.rQuery(
            'SELECT name, school FROM groupdata WHERE groupId = %s',
            (gid,)
        )
        for (name, school) in group:
            return {
                'groupId': gid,
                'name': name,
                'school': school,
            }

        abort(404)
