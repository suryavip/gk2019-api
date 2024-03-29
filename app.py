import firebase_admin
from flask import Flask, request
from flask_restful import Api, Resource
from privateConfig import PrivateConfig

from user import User, Profiles
from fcmToken import FCMToken
from feedback import Feedback, Feedbacks
from maintenance import CleanUp

from group import Group, GroupInfo
from notification import Notification
from member import Member
from schedule import Schedule
from assignment import Assignment
from exam import Exam
from opinion import Opinion
from attachment import TempAttachment, Attachment
from profile_pic import SelfProfilePic, ProfilePic

from connection import MysqlCon, FirebaseCon

import time

app = Flask(__name__, static_url_path='')
app.secret_key = PrivateConfig.flaskSecretKey
api = Api(app)

cred = firebase_admin.credentials.Certificate('pythonAdminSDKPrivateKey.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://rk2019-rk2019.firebaseio.com/',
    'storageBucket': 'rk2019-rk2019.appspot.com',
})


@app.after_request
def after_request(response):
    requesterOrigin = request.environ.get('HTTP_ORIGIN', 'default value')
    if requesterOrigin != 'http://localhost' and requesterOrigin != 'https://grupkelas.boostedcode.com':
        requesterOrigin = 'http://localhost'
    response.headers["Access-Control-Allow-Origin"] = requesterOrigin
    response.headers["Access-Control-Allow-Headers"] = "Accept, Accept-Language, Content-Language, Content-Type, X-idToken, X-timestamp"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"

    requestMethod = request.environ.get('REQUEST_METHOD')
    if requestMethod == 'OPTIONS':
        time.sleep(1)

    return response


class Test(Resource):
    def get(self):
        MysqlCon()
        FirebaseCon()
        return {'hello': 'World, Firebase and MySQL connected!'}


api.add_resource(Test, '/test')

api.add_resource(CleanUp, '/maintenance/cleanup')

api.add_resource(User, '/user')
api.add_resource(Profiles, '/profiles')
api.add_resource(GroupInfo, '/groupInfo/<string:gid>')

api.add_resource(FCMToken, '/fcmToken')

api.add_resource(Feedback, '/feedback')
api.add_resource(Feedbacks, '/feedback/<string:appVersion>')

api.add_resource(TempAttachment, '/storage/attachment')
api.add_resource(Attachment, '/storage/attachment/<string:aid>')

api.add_resource(SelfProfilePic, '/storage/profile_pic')
api.add_resource(ProfilePic, '/storage/profile_pic/<string:uid>')

# cache table name (channel): group
# only group channel that not need for groupId/userId
api.add_resource(Group, '/group')

# cache channel: notification
api.add_resource(Notification, '/notification')

# cache channel: member/<gid>
api.add_resource(Member, '/member/<string:gid>')

# cache channel: schedule/<owner>
api.add_resource(Schedule, '/schedule/<string:owner>')

# cache channel: assignment/<owner>
api.add_resource(Assignment, '/assignment/<string:owner>')

# cache channel: exam/<owner>
api.add_resource(Exam, '/exam/<string:owner>')

# cache channel: opinion
api.add_resource(Opinion, '/opinion')

if __name__ == '__main__':
    app.run(debug=True)
