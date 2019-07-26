def getGroupName(mysqlCon, gid):
    # getting old data
    d = mysqlCon.rQuery(
        'SELECT name FROM groupdata WHERE groupId = %s',
        (gid,)
    )
    for (name,) in d:
        return name
    return ''

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