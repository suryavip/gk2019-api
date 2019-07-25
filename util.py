def getGroupName(mysqlCon, gid):
    # getting old data
    d = mysqlCon.rQuery(
        'SELECT name FROM groupdata WHERE groupId = %s',
        (gid,)
    )
    for (name,) in d:
        return name
    return ''