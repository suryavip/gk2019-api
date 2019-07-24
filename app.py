import firebase_admin
from flask import Flask, request
from flask_restful import Api, Resource
from privateConfig import PrivateConfig

from user import User, Profiles
from group import Group

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
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-idToken, X-oldFCMToken, X-newFCMToken"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE"
    return response


class Test(Resource):
    def get(self):
        return {'hello': 'World'}


api.add_resource(Test, '/test')

api.add_resource(User, '/user')
api.add_resource(Profiles, '/profiles')

# cache table name (channel): group
api.add_resource(Group, '/group')

if __name__ == '__main__':
    app.run(debug=True)
