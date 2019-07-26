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

        '''self.cleanParentlessChilds()
        # to match this action, client should cleanup parentless childs

        self.cleanExpiredParents()
        # to match this action, client should cleanup expired parents and its childs

        self.cleanOldActivities()
        # to match this action, client should cleanup old activities

        self.cleanAttachments()'''

        self.mysqlCon.db.commit()

        self.log.write('finish: {}\n\n'.format(datetime.now().isoformat()))
        self.log.close()

        return {}

    def cleanOldNotifications(self):
        self.log.write('cleaning old notifications...\n')
        self.mysqlCon.rQuery(
            'DELETE FROM notificationdata WHERE notificationTime < SUBDATE(CURRENT_DATE, 4)' # 3 + 1 for timezone margin
        )
        self.log.write('old notifications cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanExpiredAssignments(self):
        self.log.write('cleaning expired assignments...\n')
        self.mysqlCon.rQuery(
            'DELETE FROM assignmentdata WHERE dueDate < SUBDATE(CURRENT_DATE, 1)' # + 1 for timezone margin
        )
        self.log.write('expired assignments cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanExpiredExams(self):
        self.log.write('cleaning expired exams...\n')
        self.mysqlCon.rQuery(
            'DELETE FROM examdata WHERE examDate < SUBDATE(CURRENT_DATE, 1)' # + 1 for timezone margin
        )
        self.log.write('expired exams cleaned ({})\n'.format(self.mysqlCon.cursor.rowcount))

    '''def cleanParentlessChilds(self):
        # cleanup childs of parents that deleted more than (exclusive) 8 days ago (data is null)
        # the parents itself wont be cleaned up by this function. it will cleaned later when expired
        # SUBDATE(CURRENT_DATE, 8) means if now date is 14, result will be 6 (14-8)
        # its actually intended to be 7 days (a week) but give 1 more day for timezone margin
        self.log.write('collecting deleted parents (data is null)...\n')
        deleted = self.mysqlCon.rQuery(
            "SELECT rowId FROM saved WHERE tableName IN (%s, %s, %s) AND data IS NULL AND updateTime < SUBDATE(CURRENT_DATE, 8) AND deletedCleanedUp = %s",
            ('announcement', 'assignment', 'exam', 0)
            # schedule can't be deleted
        )

        d = ['dummy']
        for (rowId,) in deleted:
            d.append(rowId)
            self.parentsOfAttachmentToDelete[rowId] = True
        q = ', '.join(['%s'] * len(d))

        # delete childs
        self.log.write('cleaning up childs of these deleted parents ({}):\n'.format(len(d)))
        self.log.write('{}\n'.format('\n'.join(d)))

        self.mysqlCon.wQuery(
            "DELETE FROM saved WHERE tableName IN (%s, %s, %s) AND index1 IN ({})".format(q),
            tuple(['activity', 'assignmentCheck', 'examCheck'] + d)
        )
        self.log.write('parentless childs (except attachments) are cleaned up (affected: {})\n'.format(self.mysqlCon.cursor.rowcount))

        # mark deletedCleanedUp
        self.mysqlCon.wQuery(
            "UPDATE saved SET deletedCleanedUp = %s WHERE rowId IN ({})".format(q),
            tuple([1] + d)
        )
        self.log.write('clean deleted parents are marked (affected: {})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanExpiredParents(self):
        # cleanup parents and its childs that expired (before yesterday)
        # its actually intended to be "before today" but give 1 more day for timezone margin
        # SUBDATE(CURRENT_DATE, 1) means yesterday
        self.log.write('collecting expired parents...\n')
        expired = self.mysqlCon.rQuery(
            "SELECT rowId FROM saved WHERE tableName IN (%s, %s, %s) AND index1 < SUBDATE(CURRENT_DATE, 1)",
            ('announcement', 'assignment', 'exam')
            # schedule will never expire
        )

        d = ['dummy']
        for (rowId,) in expired:
            d.append(rowId)
            self.parentsOfAttachmentToDelete[rowId] = True
        q = ', '.join(['%s'] * len(d))

        # delete items
        self.log.write('cleaning up expired parents ({}):\n'.format(len(d)))
        self.log.write('{}\n'.format('\n'.join(d)))

        self.mysqlCon.wQuery(
            "DELETE FROM saved WHERE rowId IN ({})".format(q),
            tuple(d)
        )
        self.log.write('expired parents are cleaned up (affected: {})\n'.format(self.mysqlCon.cursor.rowcount))

        # delete activities, assignmentCheck and examCheck
        self.log.write('cleaning up childs of expired parents...\n')
        self.mysqlCon.wQuery(
            "DELETE FROM saved WHERE tableName IN (%s, %s, %s) AND index1 IN ({})".format(q),
            tuple(['activity', 'assignmentCheck', 'examCheck'] + d)
        )
        self.log.write('childs of expired parents are cleaned up (affected: {})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanOldActivities(self):
        # cleanup activities that created older than (exclusive) 8 days ago
        # its actually intended to be 7 days but give 1 more day for timezone margin
        # SUBDATE(CURRENT_DATE, 8) means if now date is 14, result will be 6 (14-8)
        self.log.write('cleaning up old activities...\n')
        self.mysqlCon.wQuery(
            "DELETE FROM saved WHERE tableName = %s AND updateTime < SUBDATE(CURRENT_DATE, 8)",
            ('activity',)
        )
        self.log.write('old activities are cleaned up (affected: {})\n'.format(self.mysqlCon.cursor.rowcount))

    def cleanAttachments(self):
        # delete parentless attachments
        a = self.parentsOfAttachmentToDelete.keys()

        if len(a) < 1:
            self.log.write('no attachments of expired and deleted parents\n')
            return

        self.log.write('getting attachments of expired and deleted parents ({}):\n'.format(len(a)))
        self.log.write('{}\n'.format('\n'.join(a)))

        q = ','.join(['%s'] * len(a))
        attachments = self.mysqlCon.rQuery(
            'SELECT attachmentId, owner, parent FROM attachment WHERE parent IN ({})'.format(q),
            tuple(a)
        )

        # attachments path pattern: /attachment/${owner}/${parent}/${file}
        aid = ['attachment/{}/{}/{}'.format(owner, parent, attachmentId) for (attachmentId, owner, parent) in attachments]

        self.log.write('cleaning up attachments from firebase storage ({}):\n'.format(len(aid)))
        self.log.write('{}\n'.format('\n'.join(aid)))

        notFound = []

        def reportNotFound(p):
            notFound.append(p)

        bucket = self.fbc.storage.bucket()
        bucket.delete_blobs(aid, on_error=reportNotFound)

        # log if error occours
        if len(notFound) > 0:
            self.log.write('SOME ATTACHMENTS ({}) NOT FOUND ON FIREBASE STORAGE:\n'.format(len(notFound)))
            self.log.write('{}\n'.format('\n'.join(notFound)))

        # delete tracked attachment
        self.log.write('cleaning up tracked attachments...\n')
        self.mysqlCon.wQuery(
            "DELETE FROM attachment WHERE parent IN ({})".format(q),
            tuple(a)
        )
        self.log.write('tracked attachments are cleaned up (affected: {})\n'.format(self.mysqlCon.cursor.rowcount))

        self.log.write('attachments of deleted and expired parents are cleaned up\n')'''
