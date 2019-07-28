from flask_restful import Resource

from connection import FirebaseCon, MysqlCon
from datetime import datetime


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
        self.mysqlCon.rQuery(
            'DELETE FROM notificationdata WHERE notificationTime < SUBDATE(CURRENT_DATE, 4)'  # 3 + 1 for timezone margin
        )
        self.log.write('old notifications cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanExpiredAssignments(self):
        self.log.write('cleaning expired assignments...\n')
        self.mysqlCon.rQuery(
            'DELETE FROM assignmentdata WHERE dueDate < SUBDATE(CURRENT_DATE, 1)'  # + 1 for timezone margin
        )
        self.log.write('expired assignments cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanExpiredExams(self):
        self.log.write('cleaning expired exams...\n')
        self.mysqlCon.rQuery(
            'DELETE FROM examdata WHERE examDate < SUBDATE(CURRENT_DATE, 1)'  # + 1 for timezone margin
        )
        self.log.write('expired exams cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))

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
