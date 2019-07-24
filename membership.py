from connection import MysqlCon

validLevel = ['admin', 'member', 'pending']


class MembersOfGroup():
    def __init__(self, gid, requester='', target='', returnWithName=False):
        mysqlCon = MysqlCon()

        if returnWithName:
            result = mysqlCon.rQuery(
                'SELECT memberdata.userId, memberdata.level, userdata.name FROM memberdata JOIN userdata ON memberdata.userId = userdata.userId WHERE memberdata.groupId = %s',
                (gid,)
            )
        else:
            result = mysqlCon.rQuery(
                'SELECT userId, level, \'\' AS name FROM memberdata WHERE groupId = %s',
                (gid,)
            )

        self.all = []
        self.byLevel = {}
        for level in validLevel:
            self.byLevel[level] = []
        self.rStatus = ''
        self.tStatus = ''

        for (userId, level, name) in result:
            if level not in validLevel:
                continue

            self.byLevel[level].append(userId)
            if returnWithName:
                self.all.append({
                    'level': level,
                    'userId': userId,
                    'name': name,
                })
            else:
                self.all.append({
                    'level': level,
                    'userId': userId,
                })

            if userId == requester:
                self.rStatus = level
            if userId == target:
                self.tStatus = level
                if returnWithName:
                    self.tName = name

        self.insider = self.byLevel['admin'] + self.byLevel['member']

        # use rStatus to check requester status in a group
        # use tStatus to check target status in a group
        # to get all user joined in a group (including pending), use all
        # to get all user joined in a group with specific level, use byLevel[level]
        # to get all admin and member (no pending), use insider

    def exclude(self, all=[], exceptions=[]):
        # this will return all - exceptions
        return [i for i in all if i not in exceptions]


class GroupsOfUser():
    def __init__(self, uid, oldByGroupId={}):
        mysqlCon = MysqlCon()
        result = mysqlCon.rQuery(
            'SELECT groupId, level FROM memberdata WHERE userId = %s',
            (uid,)
        )

        # self.changed True if oldByGroupId is different from self.byGroupId, False is same
        self.changed = False
        self.all = []
        self.byLevel = {}
        self.byGroupId = {}
        for level in validLevel:
            self.byLevel[level] = []

        for (groupId, level) in result:
            if level not in validLevel:
                continue

            self.byLevel[level].append(groupId)

            if groupId not in oldByGroupId:
                self.changed = True
            elif oldByGroupId[groupId] != level:
                self.changed = True
            self.byGroupId[groupId] = level

            self.all.append({
                'groupId': groupId,
                'level': level,
            })

        if self.changed == False:
            for groupId in oldByGroupId:
                level = oldByGroupId[groupId]
                if groupId not in self.byGroupId:
                    self.changed = True
                elif self.byGroupId[groupId] != level:
                    self.changed = True

        # use rStatus to check requester status in a group
        # use tStatus to check target status in a group
        # to get all user joined in a group (including pending), use all
        # to get all user joined in a group with specific level, use byLevel[level]