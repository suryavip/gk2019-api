from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup
from sendNotification import SendNotification
from util import getGroupName, verifyTime
import json


class Schedule(Resource):
    def put(self, owner):  # edit schedule
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('day', required=True, help='day', type=int)
        parser.add_argument('data', default=[], action='append', type=dict)
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

        # check for valid day
        if args['day'] not in range(7):
            abort(400, code='invalid scheduleId')
        scheduleId = '{}schedule{}'.format(owner, args['day'])

        # verify data
        for i in args['data']:
            if 'subject' not in i or 'time' not in i or 'length' not in i:
                abort(400, code='invalid data')
            if isinstance(i['subject'], str) != True or len(i['subject']) < 1:
                abort(400, code='invalid subject data')
            if isinstance(i['time'], str) != True or verifyTime(i['time']) != True:
                abort(400, code='invalid time data')
            if isinstance(i['length'], int) != True:
                abort(400, code='invalid length data')

        # store data
        mysqlCon.insertQuery('scheduledata', [{
            'scheduleId': scheduleId,
            ownerCol: owner,
            'data': json.dumps(args['data'])
        }], updateOnDuplicate=True)

        if mysqlCon.cursor.rowcount < 1:
            return self.get(owner)

        rdbPathUpdate = []
        if len(mog.all) > 0:
            # send notif to insider except self
            SendNotification(
                mog.exclude(mog.insider, [fbc.uid]),
                'schedule-edit',
                data={
                    'groupId': owner,
                    'groupName': getGroupName(mysqlCon, owner),
                    'performerUserId': fbc.uid,
                    'performerName': fbc.decoded_token['name'],
                    'scheduleId': scheduleId,
                    'day': args['day'],
                },
                tag='schedule-{}'.format(scheduleId),
            )
            rdbPathUpdate = ['poke/{}/schedule/{}'.format(u, owner) for u in mog.insider]
        else:
            rdbPathUpdate.append('poke/{}/schedule/{}'.format(fbc.uid, owner))

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

        schedule = mysqlCon.rQuery(
            'SELECT scheduleId, data FROM scheduledata WHERE {} = %s'.format(ownerCol),
            (owner,)
        )

        result = []
        for (scheduleId, data) in schedule:
            result.append({
                'scheduleId': scheduleId,
                'data': json.loads(data),
            })

        return result
