def fetch_field(obj, *fields):
    cursor = obj

    for f in fields:
        if cursor is None:
            break
        cursor = cursor.get(f)

    return cursor
