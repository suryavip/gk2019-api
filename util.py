from rules import Rules
from datetime import date, time
import os

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
    # attachmentId is filename on server
    if len(attachment) > Rules.maxAttachmentPerItem:
        return False
        
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


def saveUploadedFile(source, destination, acceptedTypes, maxSize, thumbSource=None):
    thumbDestination = '{}_thumb'.format(destination)

    # check mimetype
    if source.mimetype not in acceptedTypes:
        return 'unknown type'
    if thumbSource != None:
        if thumbSource.mimetype not in acceptedTypes:
            return 'unknown thumb type'

    # try saving
    try:
        source.save(destination)
    except:
        return 'failed to write'
    if thumbSource != None:
        try:
            thumbSource.save(thumbDestination)
        except:
            os.remove(destination)
            return 'failed to write thumb'

    # check file size
    if os.stat(destination).st_size > maxSize:
        os.remove(destination)
        if thumbSource != None:
            os.remove(thumbDestination)
        return 'file size is too big'

    if thumbSource != None:
        if os.stat(thumbDestination).st_size > maxSize:
            os.remove(destination)
            os.remove(thumbDestination)
            return 'thumb size is too big'

    return True