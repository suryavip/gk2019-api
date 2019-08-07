from datetime import date, time

def getGroupName(mysqlCon, gid):
    # getting old data
    return getSingleField(mysqlCon, 'name', 'groupdata', 'groupId', gid)


def getSingleField(mysqlCon, colName, tableName, idColName, rowId, default=''):
    # getting old data
    d = mysqlCon.rQuery(
        'SELECT {} FROM {} WHERE {} = %s'.format(colName, tableName, idColName),
        (rowId,)
    )
    for (a,) in d:
        return a
    return default


def verifyTime(timeInput):
    # verify if HH:MM format (isoformat without sec and microsec)
    try:
        t = timeInput.split(':')
        timeV = time(hour=int(t[0]), minute=int(t[1])).isoformat(timespec='minutes')
    except:
        return False
    return timeInput == timeV


def verifyDate(dateInput):
    # verify if YYYY-MM-DD format (isoformat)
    try:
        dateIn = dateInput.split('-')
        dateV = date(int(dateIn[0]), int(dateIn[1]), int(dateIn[2])).isoformat()
    except:
        return False
    return dateInput == dateV


def validateAttachment(attachment):
    # all attachment must be dict containing originalFilename (optional for rename on download) and attachmentId (required)
    # attachmentId is filename on firebase storage
    # on firebase, file are stored with this path: attachment/${ownerId}/${attachmentId}
    for a in attachment:
        if isinstance(a, dict) != True:
            return False

        if 'attachmentId' not in a:
            return False
        if isinstance(a['attachmentId'], str) != True:
            return False

    return True


def updateAttachment(mysqlCon, new, ownerCol, owner, parentColName, parentId):
    c = mysqlCon.rQuery(
        'SELECT attachmentId FROM attachmentdata WHERE {} = %s'.format(parentColName),
        (parentId,)
    )
    deleted = [aid for (aid,) in c if aid not in new]
    
    if len(deleted) > 0:
        q = ['%s'] * len(deleted)
        q = ','.join(q)
        mysqlCon.wQuery(
            'UPDATE attachmentdata SET deleted = 1 WHERE attachmentId IN ({})'.format(q),
            tuple(deleted)
        )

    attachmentdata = [{
        'attachmentId': a['attachmentId'],
        ownerCol: owner,
        parentColName: parentId,
        'originalFilename': a['originalFilename'],
    } for a in new]

    if len(attachmentdata) > 0:
        mysqlCon.insertQuery('attachmentdata', attachmentdata, updateOnDuplicate=True)
