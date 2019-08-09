from connection import MysqlCon, FirebaseCon
import requests
import threading
import json
import uuid
import time
from privateConfig import PrivateConfig


class SendNotification():
    def __init__(self, targetUser, notifType, data={}, tag=''):
        if len(targetUser) == 0:
            return
        mysqlCon = MysqlCon()
        fbc = FirebaseCon()
        n = []
        batchId = str(uuid.uuid4())
        for t in targetUser:
            n.append({
                'batchId': batchId,
                'targetUserId': t,
                'notificationType': notifType,
                'notificationData': json.dumps(data),
            })
        
        mysqlCon.insertQuery('notificationdata', n)

        fbc.updateRDBTimestamp(int(time.time()), ['poke/{}/notification'.format(t) for t in targetUser])

        mysqlCon.db.commit()

        threading.Thread(target=self.push, args=[targetUser, notifType, data, tag]).start()

    def translate(self, notifType, langKey, data={}):
        lang = {
            'id': {
                'assignment-new': '',
                'assignment-edit': '',
                'assignment-delete': '',
                'exam-new': '',
                'exam-edit': '',
                'exam-delete': '',
                'test': 'Ini adalah tes push notification',
                'group-edit': '{performerName} mengubah info grup {groupName}',
                'pending-new': '{performerName} meminta bergabung kedalam grup {groupName}',
                'member-new-target': '{performerName} menerima kamu bergabung kedalam grup {groupName}',
                'member-new': '{performerName} menerima {targetName} bergabung kedalam grup {groupName}',
                'admin-new-target': '{perormerName} menjadikan kamu sebagai admin grup {groupName}',
                'admin-new': '{performerName} menjadikan {targetName} sebagai admin grup {groupName}',
                'admin-stop': '{performerName} berhenti menjadi admin grup {groupName}',
                'member-delete-self': '{performerName} keluar dari grup {groupName}',
                'member-delete': '{performerName} mengeluarkan {targetName} dari grup {groupName}',
                'admin-delete': '{performerName} keluar dari grup {groupName}',
                'schedule-edit': '',
            },
            'en': {
                'assignment-new': '',
                'assignment-edit': '',
                'assignment-delete': '',
                'exam-new': '',
                'exam-edit': '',
                'exam-delete': '',
                'test': 'This is the push notification test',
                'group-edit': '{performerName} changed {groupName} group info\'s',
                'pending-new': '{performerName} asked to join {groupName}',
                'member-new-target': '{performerName} accepted you to join {groupName}',
                'member-new': '{performerName} accepted {targetName} to join {groupName}',
                'admin-new-target': '{performerName} promoted you as admin of {groupName}',
                'admin-new': '{performerName} promoted {targetName} as admin of {groupName}',
                'admin-stop': '{performerName} stopped from being admin of {groupName}',
                'member-delete-self': '{performerName} left from {groupName}',
                'member-delete': '{performerName} kicked {targetName} from {groupName}',
                'admin-delete': '{performerName} left from {groupName}',
                'schedule-edit': '',
            },
        }

        if langKey not in lang:
            langKey = 'id'  # default

        return lang[langKey][notifType].format_map(data)

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
