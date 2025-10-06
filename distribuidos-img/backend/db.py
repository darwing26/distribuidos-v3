import pymysql

def get_conn():
    return pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="admin1",
        database="distribuidos_img",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
