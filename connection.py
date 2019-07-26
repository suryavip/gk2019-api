from flask_restful import abort
from firebase_admin import db, auth, storage
from privateConfig import PrivateConfig
import mysql.connector
import threading
import socket
hostname = socket.gethostname()


class FirebaseCon:
    def __init__(self, idToken=None):
        if idToken != None:
            try:
                self.decoded_token = auth.verify_id_token(idToken, check_revoked=True)
                self.uid = self.decoded_token['uid']
            except auth.AuthError as err:
                abort(401, code='Token-{}'.format(err.code), message='{}'.format(err))
            except ValueError as err:
                abort(400, code='Token-ValueError', message='{}'.format(err))
        self.db = db
        self.auth = auth
        self.storage = storage

    def updateRDBTimestamp(self, paths):
        # paths is list
        rdbUpdate = {}
        for i in paths:
            rdbUpdate[i] = {'.sv': 'timestamp'}

        def doWork():
            ref = self.db.reference('')
            ref.update(rdbUpdate)
        threading.Thread(target=doWork, args=[]).start()


class MysqlCon:
    def __init__(self):
        if hostname == 'mirana.jagoanhosting.com':
            self.db = mysql.connector.connect(
                host='boostedcode.com',
                user='boostedc_gk2019',
                password=PrivateConfig.mysqlPassword,
                database='boostedc_gk2019'
            )
        else:
            self.db = mysql.connector.connect(
                user='root',
                password='',
                database='gk2019'
            )
        self.cursor = self.db.cursor()
        self.Error = mysql.connector.Error

    def rQuery(self, query, param=(), errorHandler={}):
        try:
            self.cursor.execute((query), param)
        except self.Error as err:
            if '{}'.format(err.errno) in errorHandler:
                thisError = errorHandler['{}'.format(err.errno)]
                abort(thisError['httpCode'], code=thisError['code'])
            abort(400, code='{}'.format(err.errno), msg={
                'query': query,
                'param': param,
            })
        result = self.cursor.fetchall()
        return result

    def wQuery(self, query, param=(), errorHandler={}):
        try:
            self.cursor.execute((query), param)
        except self.Error as err:
            if '{}'.format(err.errno) in errorHandler:
                thisError = errorHandler['{}'.format(err.errno)]
                abort(thisError['httpCode'], code=thisError['code'])
            abort(400, code='{}'.format(err.errno), msg={
                'query': query,
                'param': param,
            })

    def insertQuery(self, tableName, data, updateOnDuplicate=False, errorHandler={}):
        cols = data[0].keys()

        colsQ = ['%s'] * len(cols)
        colsQ = ','.join(colsQ)

        valsQ = ['({})'.format(colsQ)] * len(data)
        valsQ = ','.join(valsQ)

        vals = [c for c in cols]
        for r in data:
            for c in r:
                vals.append(r[c])

        query = "INSERT INTO {} ({}) VALUES {}".format(tableName, colsQ, valsQ)
        if updateOnDuplicate == True:
            dupQ = ['{} = VALUES({})'.format(c, c) for c in cols]
            query = "INSERT INTO {} ({}) VALUES {} ON DUPLICATE KEY UPDATE {}".format(tableName, colsQ, valsQ, dupQ)

        return self.wQuery(
            query,
            tuple(vals),
            errorHandler
        )
