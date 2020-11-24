import mysql.connector

from flask import g

from mysql.connector import Error
from mysql.connector import pooling

class MySQLDB:
    _db = ""
    _app = ""
    
    def __init__(self, mysql_config, role, app=None):

        dbconfig = {
            "host": mysql_config[role]["host"],
            "port": 3306, 
            "charset": 'utf8',
            "database": mysql_config["db"],
            "user": mysql_config[role]["user"],
            "password": mysql_config[role]["pass"],
        }
        if 'unix_socket' in mysql_config:
            dbconfig['unix_socket'] = mysql_config["unix_socket"]
            
        extra = ''
        if 'extra' in mysql_config:
            extra = mysql_config["extra"]
        self.published_assets_tablename = "pub_assets" + extra
        
        g._pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="dbpool",
                                                                  pool_size=8,
                                                                  pool_reset_session=True,
                                                                  **dbconfig
                                                                )
        '''
        try:
            db = getattr(g, '_database', None)
            # Establish a connection
        except:
            db = mysql.connector.pooling.MySQLConnectionPool(pool_name="dbpool",
                                                                  pool_size=8,
                                                                  pool_reset_session=True,
                                                                  **dbconfig
                                                                )
        '''
        return
            
    def published_netx_assets(self):
        sqlquery = "SELECT * FROM " + self.published_assets_tablename + ";"
        return self.query(sqlquery)
            
    def query(self, sqlquery):
        conn = g._pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(sqlquery)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results if results else None
        
    def update(self, sqlquery):
        conn = g._pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(sqlquery)
        id = cursor.lastrowid
        cursor.close()
        conn.close()
        return id
