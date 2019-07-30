from connection import MysqlCon, FirebaseCon
import requests
import threading
import json
import uuid
from privateConfig import PrivateConfig


class SendNotification():
    def __init__(self, targetUser, notifType, data={}, tag=''):
        mysqlCon = MysqlCon()
        fbc = FirebaseCon()
        n = []
        batchId = str(uuid.uuid4())
        for t in targetUser:
            n.append({
                'batchId': batchId,
                'targetUserId': t,
                'notificationType': notifType,
                'notificationData': data,
            })
        mysqlCon.insertQuery('notificationdata', n)

        fbc.updateRDBTimestamp(['poke/{}/notification'.format(t) for t in targetUser])

        mysqlCon.db.commit()

        threading.Thread(target=self.push, args=[targetUser, notifType, data, tag]).start()

    def translate(self, notifType, langKey, data={}):
        lang = {
            'id': {
                'test': 'Ini adalah tes push notification',
                'editGroup': '{} mengubah nama grup {} menjadi {}',
                'newPending': '{} meminta bergabung kedalam grup {}',
                'newMemberTarget': '{} menerima kamu bergabung kedalam grup {}',
                'newMember': '{} menerima {} bergabung kedalam grup {}',
                'deleteMemberSelf': '{} keluar dari grup {}',
                'deleteAdmin': '{} keluar dari grup {}',
                'deleteMember': '{} mengeluarkan {} dari grup {}',
                'newAdminTarget': '{} menjadikan kamu sebagai admin grup {}',
                'newAdmin': '{} menjadikan {} sebagai admin grup {}',
                'stopAdmin': '{} berhenti menjadi admin grup {}',
                'newReminder': '{} menambahkan {}: {}',
                'editReminder': '{} mengubah {}: {}',
                'deleteReminder': '{} menghapus {}: {}',
            },
            'en': {
                'test': 'This is the push notification test',
                'editGroup': '{} changed {} group\'s name to {}',
                'newPending': '{} asked to join {}',
                'newMemberTarget': '{} accepted you to join {}',
                'newMember': '{} accepted {} to join {}',
                'deleteMemberSelf': '{} left from {}',
                'deleteAdmin': '{} left from {}',
                'deleteMember': '{} kicked {} from {}',
                'newAdminTarget': '{} promoted you as admin of {}',
                'newAdmin': '{} promoted {} as admin of {}',
                'stopAdmin': '{} stopped from being admin of {}',
                'newReminder': '{} added new {}: {}',
                'editReminder': '{} changed {}: {}',
                'deleteReminder': '{} deleted {}: {}',
            },
        }

        if langKey not in lang:
            langKey = 'id'  # default

        def reminderType(rType):
            if langKey == 'id':
                rt = 'tugas' if rType == 'homework' else ''
                rt = 'ujian' if rType == 'exam' else rt
            elif langKey == 'en':
                rt = rType
            return rt

        if notifType == 'test':
            o = lang[langKey][notifType]
        elif notifType == 'editGroup':
            o = lang[langKey][notifType].format(data['performer']['name'], data['oldName'], data['newName'])
        elif notifType == 'newPending':
            o = lang[langKey][notifType].format(data['performer']['name'], data['groupName'])
        elif notifType == 'newMemberTarget':
            o = lang[langKey][notifType].format(data['performer']['name'], data['groupName'])
        elif notifType == 'newMember':
            o = lang[langKey][notifType].format(data['performer']['name'], data['target']['name'], data['groupName'])
        elif notifType == 'deleteMemberSelf' or notifType == 'deleteAdmin':
            o = lang[langKey][notifType].format(data['performer']['name'], data['groupName'])
        elif notifType == 'deleteMember':
            o = lang[langKey][notifType].format(data['performer']['name'], data['target']['name'], data['groupName'])
        elif notifType == 'newAdminTarget':
            o = lang[langKey][notifType].format(data['performer']['name'], data['groupName'])
        elif notifType == 'newAdmin':
            o = lang[langKey][notifType].format(data['performer']['name'], data['target']['name'], data['groupName'])
        elif notifType == 'stopAdmin':
            o = lang[langKey][notifType].format(data['performer']['name'], data['groupName'])
        elif notifType == 'newReminder':
            o = lang[langKey][notifType].format(data['performer']['name'], reminderType(data['reminderType']), data['subject'])
        elif notifType == 'editReminder':
            o = lang[langKey][notifType].format(data['performer']['name'], reminderType(data['reminderType']), data['subject'])
        elif notifType == 'deleteReminder':
            o = lang[langKey][notifType].format(data['performer']['name'], reminderType(data['reminderType']), data['subject'])
        return o

    def push(self, targetUser, notifType, data, tag):
        data['notifType'] = notifType
        mysqlCon = MysqlCon()  # open new connection
        targetToken = {}

        if len(targetUser) < 1:
            return

        # compile language and targetToken for targetUser
        q = ['%s'] * len(targetUser)
        q = ', '.join(q)

        result = mysqlCon.rQuery(
            'SELECT fcmToken, clientLanguage FROM fcmtoken WHERE userId IN ({})'.format(q),
            tuple(targetUser)
        )
        if len(result) < 1:
            return

        # group targetToken by language
        for (fcmToken, clientLanguage) in result:
            l = 'id'  # default
            if isinstance(clientLanguage, str):
                l = clientLanguage
            if l not in targetToken:
                targetToken[l] = []
            targetToken[l].append(fcmToken)

        for (langKey, tokens) in targetToken.items():
            # prepare translation
            # send notification to each language group
            # using legacy REST API and dont wait for result
            pushData = {
                'registration_ids': tokens,
                'notification': {
                    'body': self.translate(notifType, langKey, data),
                    'sound': 'default',
                },
                'data': data,
                'time_to_live': 3 * 24 * 60 * 60,  # expire after 3 days
            }
            if tag != '':
                pushData['notification']['tag'] = tag
            headers = {
                'Authorization': 'key={}'.format(PrivateConfig.fcmLegacyServerKey),
                'Content-Type': 'application/json',
            }
            try:
                r = requests.post('https://fcm.googleapis.com/fcm/send', timeout=3, data=json.dumps(pushData), headers=headers)
                if r.status_code != 200:
                    print('failed to send fcm')
                    print(r.status_code)
                    print(r.text)
            except requests.exceptions.Timeout:
                pass

        return
