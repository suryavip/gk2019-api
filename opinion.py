from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from membership import MembersOfGroup
from sendNotification import SendNotification
from util import getGroupName, getSingleField, verifyDate, validateAttachment, updateAttachment
import uuid


class Opinion(Resource):
    def put(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('X-timestamp', required=True, type=int, location='headers')
        parser.add_argument('assignmentId')
        parser.add_argument('examId')
        parser.add_argument('checked', default=False, type=bool)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        # check parent id is not null
        if 'assignmentId' in args:
            parentCol = 'assignmentId'
        elif 'examId' in args:
            parentCol = 'examId'
        else:
            abort(400, code='assignmentId or examId is required')

        oid = '{}opinion{}'.format(fbc.uid, args[parentCol])

        # store data
        mysqlCon.insertQuery('opiniondata', [{
            'opinionId': oid,
            'ownerUserId': fbc.uid,
            parentCol: args[parentCol],
            'checked': args['checked'],
        }], updateOnDuplicate=True)

        if mysqlCon.cursor.rowcount < 1:
            return self.get()

        rdbPathUpdate = ['poke/{}/opinion'.format(fbc.uid)]
        fbc.updateRDBTimestamp(args['X-timestamp'], rdbPathUpdate)

        mysqlCon.db.commit()

        return self.get()

    def get(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        opinion = mysqlCon.rQuery(
            'SELECT assignmentId, examId, checked FROM opiniondata WHERE ownerUserId = %s',
            (fbc.uid,)
        )

        result = {}
        for (assignmentId, examId, checked) in opinion:
            if assignmentId != None:
                parentId = assignmentId
            else:
                parentId = examId

            result[parentId] = {'checked': checked}

        return result
