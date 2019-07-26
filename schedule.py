from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup, GroupsOfUser
from notification import Notification
from rules import Rules
from util import getGroupName, verifyTime
import uuid
import json


class Schedule(Resource):
    def put(self, owner):  # edit schedule
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('day', required=True, help='day', type=int)
        parser.add_argument('data', required=True, help='data', type=list)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        mog = MembersOfGroup(owner, fbc.uid)

        # check for valid privilege (only if owner is groupId)
        if len(mog.all) > 0:
            ownerCol = 'ownerGroupId'
            if mog.rStatus != 'admin' and mog.rStatus != 'member':
                abort(400, code='requester is not in group')
        else:
            ownerCol = 'ownerUserId'

        # check for valid day
        if args['day'] not in range(7):
            abort(400, code='invalid scheduleId')
        scheduleId = '{}schedule{}'.format(owner, args['day'])

        # verify data
        for i in args['data']:
            if 'subject' not in i or 'time' not in i or 'length' not in i:
                abort(400, code='invalid data')
            if isinstance(i['subject'], str) != True:
                abort(400, code='invalid subject data')
            if isinstance(i['time'], str) != True or verifyTime(i['length']) != True:
                abort(400, code='invalid time data')
            if isinstance(i['length'], int) != True:
                abort(400, code='invalid length data')

        # store data
        mysqlCon.insertQuery('scheduledata', [{
            'scheduleId': scheduleId,
            ownerCol: owner,
            'data': json.dumps(args['data'])
        }], updateOnDuplicate=True)

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            Notification(
                mog.exclude(mog.insider, [fbc.uid]),
                'schedule-edit',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                },
                tag='schedule-edit-{}'.format(owner),
            )
            rdbPathUpdate = ['poke/{}/schedule/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/schedule/{}'.format(fbc.uid, owner))

        fbc.updateRDBTimestamp(rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get(owner)

    def get(self, owner):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        group = mysqlCon.rQuery(
            'SELECT groupId, userId, level FROM memberdata WHERE userId = %s AND level IN (%s, %s)',
            (fbc.uid, 'admin', 'member')
        )
        # don't return memberdata where this requester still pending
        result = {}
        for (groupId, userId, level) in group:
            if groupId not in result:
                result[groupId] = {}
            result[groupId][userId] = level

        return result
