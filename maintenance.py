from flask_restful import Resource

from util import updateAttachment

from connection import FirebaseCon, MysqlCon
from datetime import datetime, timedelta


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

        self.cleanTemporaryAttachments()

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
        c = self.mysqlCon.rQuery('SELECT attachmentId, ownerUserId, ownerGroupId FROM attachmentdata WHERE deleted = 1')
        aid = [a for (a, u, g) in c]
        path = []
        for (a, u, g) in c:
            i = u if u != None else g
            path.append('attachment/{}/{}'.format(i, a))

        self.log.write('cleaning deleted attachments ({})...\n'.format(len(aid)))
        if len(aid) < 1:
            return

        # delete from firebase
        notFound = []

        def reportNotFound(p):
            notFound.append(p)

        bucket = self.fbc.storage.bucket()
        bucket.delete_blobs(path, on_error=reportNotFound)

        # log if error occours
        if len(notFound) > 0:
            self.log.write('some attachments ({}) not found on firebase storage:\n'.format(len(notFound)))
            self.log.write('{}\n'.format('\n'.join(notFound)))

        # delete tracked attachment
        self.log.write('cleaning up tracked attachments...\n')
        self.mysqlCon.wQuery(
            "DELETE FROM attachmentdata WHERE attachmentId IN ({})".format(','.join(['%s'] * len(aid))),
            tuple(aid)
        )
        self.log.write('tracked attachments are cleaned up ({})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanTemporaryAttachments(self):
        utcYesterday = datetime.utcnow() - timedelta(days=1)
        utcYesterdayStr = utcYesterday.strftime('%Y/%m/%d')
        prefix = 'temp_attachment/{}/'.format(utcYesterdayStr)

        bucket = self.fbc.storage.bucket()
        target = bucket.list_blobs(prefix=prefix)
        targetList = list(target)
        self.log.write('cleaning up yesterday\'s temporary attachments ({}) ({})...\n'.format(utcYesterdayStr, len(targetList)))
        bucket.delete_blobs(targetList)

        self.log.write('yesterday\'s temporary attachments cleaned\n')
