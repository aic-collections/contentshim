import sqlite3
from flask import g

class DB:
    _db = ""
    _app = ""
    
    def __init__(self, app, DBNAME):
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = sqlite3.connect(DBNAME)
        self._db = db
        self._app = app
        return
        
    def init_db(self, schemaloc):
        with self._app.app_context():
            with self._app.open_resource(schemaloc, mode='r') as f:
                self._db.cursor().executescript(f.read())
            self._db.commit()
            return True
    
    def etags(self):
        sqlquery = "SELECT * FROM etags;"
        call = self._db.execute(sqlquery)
        results = call.fetchall()
        call.close()
        return results if results else None
            
    def query(self, sqlquery):
        call = self._db.execute(sqlquery)
        results = call.fetchall()
        call.close()
        return results if results else None
        
    def update(self, sqlquery):
        call = self._db.cursor()
        call.execute(sqlquery)
        self._db.commit()
        id = call.lastrowid
        call.close()
        return id
    