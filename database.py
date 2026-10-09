import sqlite3


def get_db_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema_parts = []

    tables = cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()

    for (table,) in tables:
        columns = cursor.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()

        foreign_keys = cursor.execute(
            f'PRAGMA foreign_key_list("{table}")'
        ).fetchall()

        column_text = ", ".join(
            f"{col[1]} {col[2]}" for col in columns
        )

        schema_parts.append(
            f"Table: {table}\nColumns: {column_text}"
        )

        for fk in foreign_keys:
            # fk[2] = referenced table
            # fk[3] = source column
            # fk[4] = referenced column
            schema_parts.append(
                f"Relationship: {table}.{fk[3]} -> "
                f"{fk[2]}.{fk[4]}"
            )

    conn.close()
    return "\n".join(schema_parts)


def execute_sql(db_path, sql_query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.close()
        return columns, rows
    except Exception as e:
        print(e)
        conn.close()
        return None, None


if __name__ == '__main__':
    db_path = r"data/Chinook_Sqlite.sqlite"
    schema = get_db_schema(db_path)
    print(schema)
    # sql_query = """
    # SELECT Genre.Name, COUNT(Track.TrackId) AS track_count
    # FROM Genre
    # JOIN Track ON Genre.GenreId = Track.GenreId
    # GROUP BY Genre.Name
    # ORDER BY track_count DESC;
    # """

    # columns, rows = execute_sql(db_path, sql_query)

    # print("Columns:", columns)
    # print("Rows:")
    # for row in rows or []:
    #     print(row)