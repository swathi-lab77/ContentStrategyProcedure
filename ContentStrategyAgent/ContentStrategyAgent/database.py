import sqlite3

DATABASE = "content.db"


def get_connection():
    return sqlite3.connect(DATABASE)


def create_table():
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            topic TEXT,
            content_type TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def add_content(
    title,
    topic,
    content_type,
    views=0,
    likes=0,
    comments=0,
    shares=0
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO content
        (title, topic, content_type, views, likes, comments, shares)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        title,
        topic,
        content_type,
        views,
        likes,
        comments,
        shares
    ))

    conn.commit()
    conn.close()


def get_all_content():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            title,
            topic,
            content_type,
            views,
            likes,
            comments,
            shares
        FROM content
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


create_table()