class Rules:
    maxGroupPerUser = 10
    maxUserPerGroup = 70
    maxProfilePicSize = 1 * 1024 * 1024
    profilePicType = 'image/jpeg'
    maxAttachmentPerItem = 10
    maxAttachmentSize = 5 * 1024 * 1024
    acceptedAttachmentImageType = 'image/jpeg'
    acceptedAttachmentFileType = [
        'text/plain',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.oasis.opendocument.text',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.oasis.opendocument.presentation',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.oasis.opendocument.spreadsheet',
        'application/x-rar-compressed',
        'application/zip',
    ]
