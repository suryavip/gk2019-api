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