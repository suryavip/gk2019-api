from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup, GroupsOfUser
from notification import Notification
from rules import Rules
import uuid


class Group(Resource):
    def post(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('name', required=True, help='name')
        parser.add_argument('school', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        # check for group joined limit
        gou = GroupsOfUser(fbc.uid)
        if len(gou.all) >= Rules.maxGroupPerUser:
            abort(400, code='cannot join more than {} groups'.format(Rules.maxGroupPerUser))

        gid = uuid.uuid4()

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

        mysqlCon.db.commit()

        return self.get(), 201

    def put(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('groupId', required=True, help='groupId')
        parser.add_argument('name', required=True, help='name')
        parser.add_argument('school', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])
        gid = args['groupId']

        # check privilege
        mog = MembersOfGroup(gid, fbc.uid)
        if mog.rStatus != 'admin' and mog.rStatus != 'member':
            abort(400, code='requester is not in group')

        # getting old data
        oldData = mysqlCon.rQuery(
            'SELECT name FROM groupdata WHERE groupId = %s',
            (gid,)
        )
        oldName = ''
        for (name,) in oldData:
            oldName = name

        mysqlCon.wQuery(
            'UPDATE groupdata SET name = %s, school = %s WHERE groupId = %s',
            (args['name'], args['school'], gid)
        )
        if mysqlCon.cursor.rowcount < 1:
            abort(400, code='no changes')

        # send notif to group except self
        Notification(
            mog.exclude(mog.insider, [fbc.uid]),
            'group-edit',
            data={
                'groupId': gid,
                'groupName': oldName,
                'performerUserId': fbc.uid,
                'performerName': fbc.decoded_token['name'],
            },
            tag='group-edit-{}'.format(gid),
        )

        # poke everybody to update
        rdbPathUpdate = ['poke/{}/group'.format(u.userId) for u in mog.all]
        fbc.updateRDBTimestamp(rdbPathUpdate)

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
        result = {}
        for (groupId, name, school, level) in group:
            result[groupId] = {
                'name': name,
                'school': school,
                'level': level,
            }

        return result
