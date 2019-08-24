from flask_restful import Resource

from connection import FirebaseCon, MysqlCon
from datetime import datetime, timedelta

import os


class CleanUp(Resource):
    def post(self):
        self.mysqlCon = MysqlCon()
        self.fbc = FirebaseCon()
        self.parentsOfAttachmentToDelete = {}
        self.log = open('maintenance-log.log', 'a+')
        self.log.write('\nstart: {}\n'.format(datetime.now().isoformat()))

        self.cleanOldNotifications()

        self.cleanExpiredAssignments()

        self.cleanExpiredExams()

        self.cleanDeletedAttachments()

        self.mysqlCon.db.commit()

        self.log.write('finish: {}\n\n'.format(datetime.now().isoformat()))
        self.log.close()

        return {}

    def cleanOldNotifications(self):
        self.log.write('cleaning old notifications...\n')
        self.mysqlCon.wQuery(
            'DELETE FROM notificationdata WHERE notificationTime < SUBDATE(CURRENT_DATE, 4)'  # 3 + 1 for timezone margin
        )
        self.log.write('old notifications cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanExpiredAssignments(self):
        candidate = self.mysqlCon.rQuery(
            'SELECT assignmentId FROM assignmentdata WHERE dueDate < SUBDATE(CURRENT_DATE, 1)'  # + 1 for timezone margin
        )
        deleted = [assignmentId for (assignmentId,) in candidate]
        q = ['%s'] * len(deleted)
        self.log.write('cleaning expired assignments ({})...\n'.format(len(deleted)))
        if len(deleted) < 1:
            return

        self.log.write('\n'.join(deleted))
        self.log.write('\n')

        # delete assignment
        self.mysqlCon.wQuery(
            'DELETE FROM assignmentdata WHERE assignmentId IN ({})'.format(','.join(q)),
            tuple(deleted)
        )
        self.log.write('expired assignments cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))
        # mark delete attachment
        self.mysqlCon.wQuery(
            'UPDATE attachmentdata SET deleted = 1 WHERE assignmentId IN ({})'.format(','.join(q)),
            tuple(deleted)
        )
        self.log.write('mark attachments for expired assignments ({})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanExpiredExams(self):
        candidate = self.mysqlCon.rQuery(
            'SELECT examId FROM examdata WHERE examDate < SUBDATE(CURRENT_DATE, 1)'  # + 1 for timezone margin
        )
        deleted = [examId for (examId,) in candidate]
        q = ['%s'] * len(deleted)
        self.log.write('cleaning expired exam ({})...\n'.format(len(deleted)))
        if len(deleted) < 1:
            return

        self.log.write('\n'.join(deleted))
        self.log.write('\n')

        # delete assignment
        self.mysqlCon.wQuery(
            'DELETE FROM examdata WHERE examId IN ({})'.format(','.join(q)),
            tuple(deleted)
        )
        self.log.write('expired exam cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))
        # mark delete attachment
        self.mysqlCon.wQuery(
            'UPDATE attachmentdata SET deleted = 1 WHERE examId IN ({})'.format(','.join(q)),
            tuple(deleted)
        )
        self.log.write('mark attachments for expired exam ({})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanDeletedAttachments(self):
        c = self.mysqlCon.rQuery(
            'SELECT attachmentId FROM attachmentdata WHERE deleted = 1 OR (assignmentId IS NULL AND examId IS NULL AND uploadTime < DATE_SUB(NOW(), INTERVAL 1 HOUR))'
        )
        aid = [a for (a,) in c]

        if len(aid) < 1:
            self.log.write('no attachment (file or db) need to be cleaned\n')
            return

        self.log.write('cleaning deleted and expired-temporary attachments ({})...\n'.format(len(aid)))

        for a in aid:
            target = 'storage/attachment/{}'.format(a)
            thumb = 'storage/attachment/{}_thumb'.format(a)
            self.log.write('{}\n'.format(target))
            try:
                os.remove(target)
            except:
                self.log.write('{} not found\n'.format(target))
            try:
                os.remove(thumb)
            except:
                self.log.write('{} not found\n'.format(thumb))

        # delete tracked attachment
        self.log.write('cleaning up tracked attachments...\n')
        self.mysqlCon.wQuery(
            "DELETE FROM attachmentdata WHERE attachmentId IN ({})".format(','.join(['%s'] * len(aid))),
            tuple(aid)
        )
        self.log.write('tracked attachments are cleaned up ({})\n'.format(self.mysqlCon.cursor.rowcount))
