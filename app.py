import firebase_admin
from flask import Flask, request
from flask_restful import Api, Resource
from privateConfig import PrivateConfig

from connection import FirebaseCon

from user import User, Profiles
from fcmToken import FCMToken
from maintenance import CleanUp

from group import Group, GroupInfo
from notification import Notification
from member import Member
from schedule import Schedule
from assignment import Assignment
from exam import Exam
from opinion import Opinion

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
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-idToken, X-oldFCMToken, X-newFCMToken, X-timestamp"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE"
    return response


class Test(Resource):
    def get(self):
        '''fbc = FirebaseCon()
        bucket = fbc.storage.bucket()

        # moving from temp to permanent path
        source = bucket.blob('source/source.jpg')
        destination = bucket.blob('dest/dest.jpg')
        destination.rewrite(source)
        source.delete()

        # cleanup old temporary
        oldTemp = bucket.list_blobs(prefix='2019-08-19/')
        oldBlobs = list(oldTemp)
        print(len(oldBlobs))
        bucket.delete_blobs(oldBlobs)'''
        
        return {'hello': 'World'}


api.add_resource(Test, '/test')

api.add_resource(CleanUp, '/maintenance/cleanup')

api.add_resource(User, '/user')
api.add_resource(Profiles, '/profiles')
api.add_resource(GroupInfo, '/groupInfo/<string:gid>')

api.add_resource(FCMToken, '/fcmToken')

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
