from flask_restful import Resource, reqparse, abort
from connection import FirebaseCon, MysqlCon
from privateConfig import PrivateConfig
from membership import MembersOfGroup, GroupsOfUser
from datetime import datetime
import threading
import json
import uuid
import os


class User(Resource):
    def post(self):
        mysqlCon = MysqlCon()
        fbc = FirebaseCon()
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, help='name')
        parser.add_argument('email', required=True, help='email')
        parser.add_argument('school', default=None)
        parser.add_argument('password', required=True, help='password')
        args = parser.parse_args()

        uid = str(uuid.uuid4())

        mysqlCon.insertQuery('userdata', [{
            'userId': uid,
            'name': args['name'],
            'email': args['email'],
            'school': args['school'],
        }])

        try:
            fbc.auth.create_user(
                uid=uid,
                display_name=args['name'],
                email=args['email'],
                password=args['password'],
            )
        except fbc.auth.AuthError as err:
            abort(400, code='{}'.format(err.code), message='{}'.format(err))
        except ValueError as err:
            abort(400, code='ValueError', message='{}'.format(err))

        mysqlCon.db.commit()

        return {}, 201

    def put(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('name', required=True, help='name')
        parser.add_argument('school', default=None)
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        mysqlCon.wQuery("UPDATE userdata SET name = %s, school = %s WHERE userId = %s", (args['name'], args['school'], fbc.uid))

        try:
            fbc.auth.update_user(fbc.uid, display_name=args['name'])
        except fbc.auth.AuthError as err:
            abort(400, code='{}'.format(err.code), message='{}'.format(err))
        except ValueError as err:
            abort(400, code='ValueError', message='{}'.format(err))

        mysqlCon.db.commit()

        return {}

    def cleanup(self, fbc, rdbUpdate):
        # delete firebase rdb
        ref = fbc.db.reference('poke/{}'.format(fbc.uid))
        ref.delete()

        if len(rdbUpdate) > 0:
            # apply firebase rdb
            ref = fbc.db.reference('')
            ref.update(rdbUpdate)

    def myconverter(self, o):
        if isinstance(o, datetime):
            return o.__str__()

    def delete(self):
        mysqlCon = MysqlCon()
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        args = parser.parse_args()

        fbc = FirebaseCon(args['X-idToken'])

        # set new admin for every group that only admined by this user and still have another member
        gou = GroupsOfUser(fbc.uid)
        rdbUpdate = {}
        for groupId in gou.byLevel['admin']:
            rdbUpdate['group/{}/lastChange'.format(groupId)] = {'.sv': 'timestamp'}
            mog = MembersOfGroup(groupId, fbc.uid)
            if len(mog.byLevel['admin']) > 1:
                continue
            if len(mog.byLevel['member']) == 0:
                # no one left on group, just this user, which will delete account
                # delete group and attachment for this group
                mysqlCon.wQuery('DELETE FROM groupdata WHERE groupId = %s', (groupId,))
                mysqlCon.wQuery('UPDATE attachmentdata SET deleted = 1 WHERE ownerGroupId = %s', (groupId,))
                # delete group
                del rdbUpdate['group/{}/lastChange'.format(groupId)]
                rdbUpdate['group/{}'.format(groupId)] = None
            else:
                # set new admin (pick first member)
                mysqlCon.wQuery(
                    'UPDATE memberdata SET level = %s WHERE userId = %s AND groupId = %s',
                    ('admin', groupId, 'member', mog.byLevel['member'][0])
                )

        # backup deleted user data
        user = mysqlCon.rQuery(
            'SELECT userId, name, email, emailVerified, registrationTime, school FROM userdata WHERE userId = %s',
            (fbc.uid,)
        )
        for (userId, name, email, emailVerified, registrationTime, school) in user:
            backup = open('deletedUser/{}.json'.format(userId), 'w+')
            backup.write(json.dumps({
                'userId': userId,
                'name': name,
                'email': email,
                'emailVerified': emailVerified,
                'registrationTime': registrationTime,
                'school': school,
                'deleteTime': datetime.now(),
            }, default=self.myconverter))

        mysqlCon.wQuery("DELETE FROM userdata WHERE userId = %s", (fbc.uid,))
        mysqlCon.wQuery('UPDATE attachmentdata SET deleted = 1 WHERE ownerUserId = %s', (fbc.uid,))

        # delete user
        fbc.auth.delete_user(fbc.uid)

        mysqlCon.db.commit()

        # clean up in separate thread
        threading.Thread(target=self.cleanup, args=[fbc, rdbUpdate]).start()

        # clean up profile pic
        try:
            os.remove('storage/profile_pic/{}'.format(fbc.uid))
            os.remove('storage/profile_pic/{}_thumb'.format(fbc.uid))
        except:
            pass

        return {}


class Profiles(Resource):
    def get(self):  # this is profile resolver
        parser = reqparse.RequestParser()
        parser.add_argument('X-idToken', required=True, help='a', location='headers')
        parser.add_argument('userId', action='append', location='args')
        args = parser.parse_args()

        FirebaseCon(args['X-idToken'])

        # getting user
        user = {}
        if args['userId'] != None and len(args['userId']) > 0:
            q = ['%s'] * len(args['userId'])
            mysqlCon = MysqlCon()
            result = mysqlCon.rQuery(
                'SELECT userId, name, school FROM userdata WHERE userId IN ({})'.format(','.join(q)),
                tuple(args['userId'])
            )
            for (userId, name, school) in result:
                user[userId] = {
                    'name': name,
                    'school': school,
                }

        return user
