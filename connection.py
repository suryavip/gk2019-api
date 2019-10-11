from flask_restful import abort
from firebase_admin import db, auth
from privateConfig import PrivateConfig
import mysql.connector
import socket
hostname = socket.gethostname()


class FirebaseCon:
    def __init__(self, idToken=None):
        if idToken != None:
            try:
                self.decoded_token = auth.verify_id_token(idToken, check_revoked=True)
                self.uid = self.decoded_token['uid']
            except:
                abort(400, code='Token-error')
        self.db = db
        self.auth = auth

    def updateRDBTimestamp(self, t, paths, toClear=[]):
        # paths is list
        rdbUpdate = {}
        for i in paths:
            rdbUpdate[i] = t

        for i in toClear:
            rdbUpdate[i] = None

        ref = self.db.reference('')
        ref.update(rdbUpdate)


class MysqlCon:
    def __init__(self):
        if hostname == 'mirana.jagoanhosting.com':
            self.db = mysql.connector.connect(
                host='boostedcode.com',
                user='boostedc_gk2019',
                password=PrivateConfig.mysqlPassword,
                database='boostedc_gk2019',
                connection_timeout=10,
                unix_socket='/tmp/mysql.sock'
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

        colsN = ','.join(cols)

        colsQ = ['%s'] * len(cols)
        colsQ = ','.join(colsQ)

        valsQ = ['({})'.format(colsQ)] * len(data)
        valsQ = ','.join(valsQ)

        vals = []
        for r in data:
            for c in r:
                vals.append(r[c])

        query = "INSERT INTO {} ({}) VALUES {}".format(tableName, colsN, valsQ)
        if updateOnDuplicate == True:
            dupQ = ['{} = VALUES({})'.format(c, c) for c in cols]
            dupQ = ','.join(dupQ)
            query = "INSERT INTO {} ({}) VALUES {} ON DUPLICATE KEY UPDATE {}".format(tableName, colsN, valsQ, dupQ)

        return self.wQuery(
            query,
            tuple(vals),
            errorHandler
        )
