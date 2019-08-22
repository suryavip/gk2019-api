from datetime import datetime, date, time
import threading

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
        'SELECT attachmentId FROM attachmentdata WHERE {} = %s AND deleted = 0'.format(parentColName),
        (parentId,)
    )
    notDeleted = [a['attachmentId'] for a in new]
    deleted = [aid for (aid,) in c if aid not in notDeleted]

    changed = False
    
    if len(deleted) > 0:
        q = ['%s'] * len(deleted)
        q = ','.join(q)
        mysqlCon.wQuery(
            'UPDATE attachmentdata SET deleted = 1 WHERE attachmentId IN ({})'.format(q),
            tuple(deleted)
        )
        if mysqlCon.cursor.rowcount > 0:
            changed = True

    attachmentdata = [{
        'attachmentId': a['attachmentId'],
        ownerCol: owner,
        parentColName: parentId,
        'originalFilename': None if 'originalFilename' not in a else a['originalFilename'],
    } for a in new]

    if len(attachmentdata) > 0:
        mysqlCon.insertQuery('attachmentdata', attachmentdata, updateOnDuplicate=True)
        if mysqlCon.cursor.rowcount > 0:
            changed = True

    return changed

def moveFromTempAttachment(fbc, uploadDate, attachments, owner):
    threading.Thread(target=actualMoveFromTempAttachment, args=[fbc, uploadDate, attachments, owner]).start()

def actualMoveFromTempAttachment(fbc, uploadDate, attachments, owner):
    log = open('moveFromTempAttachment.log', 'a+')

    requester = fbc.uid
    bucket = fbc.storage.bucket()
    formatedDate = datetime.strptime(uploadDate, '%Y-%m-%d').strftime('%Y/%m/%d')

    log.write('\nmoveFromTempAttachment start: ({} attachments at {} UTC\n'.format(len(attachments), formatedDate))

    toBeDeleted = []

    for a in attachments:
        path = 'temp_attachment/{}/{}/{}'.format(formatedDate, requester, a['attachmentId'])
        source = bucket.blob(path)
        if source.exists():
            destination = bucket.blob('attachment/{}/{}'.format(owner, a['attachmentId']))
            destination.rewrite(source)
            log.write('moved\n')
            toBeDeleted.append(source)
        else:
            log.write('not found\n')

        # handle thumbnail too
        thumb = bucket.blob('temp_attachment/{}/{}/{}_thumb'.format(formatedDate, requester, a['attachmentId']))
        if thumb.exists():
            thumbD = bucket.blob('attachment/{}/{}_thumb'.format(owner, a['attachmentId']))
            thumbD.rewrite(thumb)
            log.write('thumb moved\n')
            toBeDeleted.append(thumb)
        else:
            log.write('thumb not found\n')

    bucket.delete_blobs(toBeDeleted)
