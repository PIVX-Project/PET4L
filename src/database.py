import logging
import sqlite3
import threading

from constants import database_File, trusted_RPC_Servers, trusted_explorers
from misc import printDbg, getCallerName, getFunctionName, printException


class Database:
    def __init__(self, app):
        printDbg("DB: Initializing...")
        self.app = app
        self.file_name = database_File
        self.lock = threading.Lock()
        self.isOpen = False
        self.conn = None
        printDbg("DB: Initialized")

    def openDB(self):
        printDbg("DB: Opening...")
        if self.isOpen:
            raise Exception("Database already open")

        with self.lock:
            try:
                if self.conn is None:
                    self.conn = sqlite3.connect(self.file_name)

                self.initTables()
                self.updateExplorerServers()  # Ensure existing entries have isCustom set
                self.conn.commit()
                self.conn.close()
                self.conn = None
                self.isOpen = True
                printDbg("DB: Database open")

            except Exception as e:
                err_msg = 'SQLite initialization error'
                printException(getCallerName(), getFunctionName(), err_msg, e)

    def close(self):
        printDbg("DB: closing...")
        if not self.isOpen:
            err_msg = "Database already closed"
            printException(getCallerName(), "close()", err_msg, "")
            return

        with self.lock:
            try:
                if self.conn is not None:
                    self.conn.close()

                self.conn = None
                self.isOpen = False
                printDbg("DB: Database closed")

            except Exception as e:
                err_msg = 'SQLite closing error'
                printException(getCallerName(), getFunctionName(), err_msg, e.args)

    def getCursor(self):
        if self.isOpen:
            self.lock.acquire()
            try:
                if self.conn is None:
                    self.conn = sqlite3.connect(self.file_name)
                return self.conn.cursor()

            except Exception as e:
                err_msg = 'SQLite error getting cursor'
                printException(getCallerName(), getFunctionName(), err_msg, e.args)
                self.lock.release()

        else:
            raise Exception("Database closed")

    def releaseCursor(self, rollingBack=False, vacuum=False):
        if self.isOpen:
            try:
                if self.conn is not None:
                    # commit
                    if rollingBack:
                        self.conn.rollback()

                    else:
                        self.conn.commit()
                        if vacuum:
                            self.conn.execute('vacuum')

                    # close connection
                    self.conn.close()

                self.conn = None

            except Exception as e:
                err_msg = 'SQLite error releasing cursor'
                printException(getCallerName(), getFunctionName(), err_msg, e.args)

            finally:
                self.lock.release()

        else:
            raise Exception("Database closed")

    def initTables(self):
        printDbg("DB: Initializing tables...")
        try:
            cursor = self.conn.cursor()

            # Tables for RPC Servers
            cursor.execute("CREATE TABLE IF NOT EXISTS PUBLIC_RPC_SERVERS("
                        " id INTEGER PRIMARY KEY, protocol TEXT, host TEXT,"
                        " user TEXT, pass TEXT)")

            cursor.execute("CREATE TABLE IF NOT EXISTS CUSTOM_RPC_SERVERS("
                        " id INTEGER PRIMARY KEY, protocol TEXT, host TEXT,"
                        " user TEXT, pass TEXT)")

            # Table for Explorers
            cursor.execute("CREATE TABLE IF NOT EXISTS EXPLORER_SERVERS("
                        " id INTEGER PRIMARY KEY, url TEXT, isTestnet BOOLEAN, isCustom BOOLEAN)")

            # Add the isTestnet and isCustom columns if they don't exist
            try:
                cursor.execute("ALTER TABLE EXPLORER_SERVERS ADD COLUMN isTestnet BOOLEAN")
            except sqlite3.OperationalError as e:
                if 'duplicate column name: isTestnet' in str(e):
                    pass  # The column already exists
                else:
                    raise

            try:
                cursor.execute("ALTER TABLE EXPLORER_SERVERS ADD COLUMN isCustom BOOLEAN")
            except sqlite3.OperationalError as e:
                if 'duplicate column name: isCustom' in str(e):
                    pass  # The column already exists
                else:
                    raise

            self.initTable_RPC(cursor)
            self.initTable_Explorer(cursor)

            # Tables for Utxos
            cursor.execute("CREATE TABLE IF NOT EXISTS UTXOS("
                        " tx_hash TEXT, tx_ouput_n INTEGER, satoshis INTEGER, confirmations INTEGER,"
                        " script TEXT, receiver TEXT, staker TEXT, coinstake BOOLEAN,"
                        " PRIMARY KEY (tx_hash, tx_ouput_n))")

            cursor.execute("CREATE TABLE IF NOT EXISTS RAWTXES("
                        " tx_hash TEXT PRIMARY KEY,  rawtx TEXT, lastfetch INTEGER)")

            printDbg("DB: Tables initialized")

        except Exception as e:
            err_msg = 'error initializing tables'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)

    def initTable_Explorer(self, cursor):
        s = trusted_explorers
        for idx, explorer in enumerate(s):
            url, isTestnet, isCustom = explorer
            cursor.execute("INSERT OR IGNORE INTO EXPLORER_SERVERS (id, url, isTestnet, isCustom) VALUES (?, ?, ?, ?)",
                        (idx, url, isTestnet, isCustom))

    def initTable_RPC(self, cursor):
        s = trusted_RPC_Servers
        # Insert Default public trusted servers
        cursor.execute("INSERT OR REPLACE INTO PUBLIC_RPC_SERVERS VALUES"
                       " (?, ?, ?, ?, ?),"
                       " (?, ?, ?, ?, ?),"
                       " (?, ?, ?, ?, ?);",
                       (0, s[0][0], s[0][1], s[0][2], s[0][3],
                        1, s[1][0], s[1][1], s[1][2], s[1][3],
                        2, s[2][0], s[2][1], s[2][2], s[2][3]))

        # Insert Local wallet
        cursor.execute("INSERT OR IGNORE INTO CUSTOM_RPC_SERVERS VALUES"
                       " (?, ?, ?, ?, ?);",
                       (0, "http", "127.0.0.1:51473", "rpcUser", "rpcPass"))

    '''
    General methods
    '''

    def clearTable(self, table_name):
        printDbg("DB: Clearing table %s..." % table_name)
        cleared_RPC = False
        try:
            cursor = self.getCursor()
            cursor.execute("DELETE FROM %s" % table_name)
            # in case, reload default RPC and emit changed signal
            if table_name == 'CUSTOM_RPC_SERVERS':
                self.initTable_RPC(cursor)
                cleared_RPC = True
            printDbg("DB: Table %s cleared" % table_name)

        except Exception as e:
            err_msg = 'error clearing %s in database' % table_name
            printException(getCallerName(), getFunctionName(), err_msg, e.args)

        finally:
            self.releaseCursor(vacuum=True)
            if cleared_RPC:
                self.app.sig_changed_rpcServers.emit()

    def removeTable(self, table_name):
        printDbg("DB: Dropping table %s..." % table_name)
        try:
            cursor = self.getCursor()
            cursor.execute("DROP TABLE IF EXISTS %s" % table_name)
            printDbg("DB: Table %s removed" % table_name)

        except Exception as e:
            err_msg = 'error removing table %s from database' % table_name
            printException(getCallerName(), getFunctionName(), err_msg, e.args)

        finally:
            self.releaseCursor(vacuum=True)

    '''
    RPC servers methods
    '''

    def addRPCServer(self, protocol, host, user, passwd):
        printDbg("DB: Adding new RPC server...")
        added_RPC = False
        try:
            cursor = self.getCursor()

            cursor.execute("INSERT INTO CUSTOM_RPC_SERVERS (protocol, host, user, pass) "
                           "VALUES (?, ?, ?, ?)",
                           (protocol, host, user, passwd)
                           )
            added_RPC = True
            printDbg("DB: RPC server added")

        except Exception as e:
            err_msg = 'error adding RPC server entry to DB'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
        finally:
            self.releaseCursor()
            if added_RPC:
                self.app.sig_changed_rpcServers.emit()

    def editRPCServer(self, protocol, host, user, passwd, id):
        printDbg("DB: Editing RPC server with id %d" % id)
        changed_RPC = False
        try:
            cursor = self.getCursor()

            cursor.execute("UPDATE CUSTOM_RPC_SERVERS "
                           "SET protocol = ?, host = ?, user = ?, pass = ?"
                           "WHERE id = ?",
                           (protocol, host, user, passwd, id)
                           )
            changed_RPC = True

        except Exception as e:
            err_msg = 'error editing RPC server entry to DB'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
        finally:
            self.releaseCursor()
            if changed_RPC:
                self.app.sig_changed_rpcServers.emit()

    def getRPCServers(self, custom, id=None):
        tableName = "CUSTOM_RPC_SERVERS" if custom else "PUBLIC_RPC_SERVERS"
        if id is not None:
            printDbg("DB: Getting RPC server with id %d from table %s" % (id, tableName))
        else:
            printDbg("DB: Getting all RPC servers from table %s" % tableName)
        try:
            cursor = self.getCursor()
            if id is None:
                cursor.execute("SELECT * FROM %s" % tableName)
            else:
                cursor.execute("SELECT * FROM %s WHERE id = ?" % tableName, (id,))
            rows = cursor.fetchall()

        except Exception as e:
            err_msg = 'error getting RPC servers from database'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
            rows = []
        finally:
            self.releaseCursor()

        server_list = []
        for row in rows:
            server = {}
            server["id"] = row[0]
            server["protocol"] = row[1]
            server["host"] = row[2]
            server["user"] = row[3]
            server["password"] = row[4]
            server["isCustom"] = custom
            server_list.append(server)

        if id is not None:
            return server_list[0]

        return server_list

    def removeRPCServer(self, id):
        printDbg("DB: Remove RPC server with id %d" % id)
        removed_RPC = False
        try:
            cursor = self.getCursor()
            cursor.execute("DELETE FROM CUSTOM_RPC_SERVERS WHERE id=?", (id,))
            removed_RPC = True

        except Exception as e:
            err_msg = 'error removing RPC server from database'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)

        finally:
            self.releaseCursor(vacuum=True)
            if removed_RPC:
                self.app.sig_changed_rpcServers.emit()

    '''
    Explorer servers methods
    '''

    def addExplorerServer(self, url, isTestnet):
        printDbg("DB: Adding new Explorer server...")
        try:
            cursor = self.getCursor()
            cursor.execute("INSERT OR IGNORE INTO EXPLORER_SERVERS (url, isTestnet, isCustom) VALUES (?, ?, ?)",
                        (url, isTestnet, True))
            printDbg("DB: Explorer server added or already exists")

        except Exception as e:
            err_msg = 'error adding Explorer server entry to DB'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
        finally:
            self.releaseCursor()
            self.app.sig_ExplorerListReloaded.emit()

    def editExplorerServer(self, url, isTestnet, id):
        printDbg("DB: Editing Explorer server with id %d" % id)
        try:
            cursor = self.getCursor()
            cursor.execute("UPDATE EXPLORER_SERVERS SET url = ?, isTestnet = ? WHERE id = ?",
                        (url, isTestnet, id))

        except Exception as e:
            err_msg = 'error editing Explorer server entry to DB'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
        finally:
            self.releaseCursor()
            self.app.sig_ExplorerListReloaded.emit()

    def getExplorerServers(self, isTestnet=None):
        tableName = "EXPLORER_SERVERS"
        printDbg("DB: Getting Explorer servers from table %s" % tableName)
        try:
            cursor = self.getCursor()
            if isTestnet is None:
                cursor.execute("SELECT * FROM %s" % tableName)
            else:
                cursor.execute("SELECT * FROM %s WHERE isTestnet = ?" % tableName, (isTestnet,))
            rows = cursor.fetchall()

        except Exception as e:
            err_msg = 'error getting Explorer servers from database'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
            rows = []
        finally:
            self.releaseCursor()

        server_list = []
        for row in rows:
            server = {}
            server["id"] = row[0]
            server["url"] = row[1]
            server["isTestnet"] = row[2]
            server["isCustom"] = row[3]
            server_list.append(server)

        return server_list

    def removeExplorerServer(self, id):
        printDbg("DB: Remove Explorer server with id %d" % id)
        try:
            cursor = self.getCursor()
            cursor.execute("DELETE FROM EXPLORER_SERVERS WHERE id = ?", (id,))
            printDbg("DB: Explorer server removed")

        except Exception as e:
            err_msg = 'error removing Explorer server from database'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
        finally:
            self.releaseCursor(vacuum=True)
            self.app.sig_ExplorerListReloaded.emit()

    def updateExplorerServers(self):
        try:
            cursor = self.getCursor()
            cursor.execute("SELECT id, url, isCustom FROM EXPLORER_SERVERS")
            rows = cursor.fetchall()

            for row in rows:
                id, url, isCustom = row
                if isCustom is None:
                    # Default to False if isCustom is not set
                    cursor.execute("UPDATE EXPLORER_SERVERS SET isCustom = ? WHERE id = ?", (False, id))
            
            self.releaseCursor()
            self.app.sig_ExplorerListReloaded.emit()
        except Exception as e:
            err_msg = 'error updating Explorer servers in database'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)



    '''
    UTXOS methods
    '''

    def rewards_from_rows(self, rows):
        rewards = []

        for row in rows:
            utxo = {}
            utxo['txid'] = row[0]
            utxo['vout'] = row[1]
            utxo['satoshis'] = row[2]
            utxo['confirmations'] = row[3]
            utxo['script'] = row[4]
            utxo['receiver'] = row[5]
            utxo['coinstake'] = row[6]
            utxo['staker'] = row[7]
            rewards.append(utxo)

        return rewards

    def addReward(self, utxo):
        logging.debug("DB: Adding reward")
        try:
            cursor = self.getCursor()
            cursor.execute("INSERT OR REPLACE INTO UTXOS "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (utxo['txid'], utxo['vout'], utxo['satoshis'], utxo['confirmations'],
                            utxo['script'], utxo['receiver'], utxo['coinstake'], utxo['staker']))
        except Exception as e:
            err_msg = 'error adding reward UTXO to DB'
            printException(getCallerName(), getFunctionName(), err_msg, e)
        finally:
            self.releaseCursor()

    def deleteReward(self, tx_hash, tx_ouput_n):
        logging.debug("DB: Deleting reward")
        try:
            cursor = self.getCursor()
            cursor.execute("DELETE FROM UTXOS WHERE tx_hash = ? AND tx_ouput_n = ?", (tx_hash, tx_ouput_n))
        except Exception as e:
            err_msg = 'error deleting UTXO from DB'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
        finally:
            self.releaseCursor(vacuum=True)

    def getReward(self, tx_hash, tx_ouput_n):
        logging.debug("DB: Getting reward")
        try:
            cursor = self.getCursor()
            cursor.execute("SELECT * FROM UTXOS WHERE tx_hash = ? AND tx_ouput_n = ?", (tx_hash, tx_ouput_n))
            rows = cursor.fetchall()
        except Exception as e:
            err_msg = 'error getting reward %s-%d' % (tx_hash, tx_ouput_n)
            printException(getCallerName(), getFunctionName(), err_msg, e)
            rows = []
        finally:
            self.releaseCursor()

        if rows:
            return self.rewards_from_rows(rows)[0]
        return None

    def getRewardsList(self, receiver=None):
        try:
            cursor = self.getCursor()
            if receiver is None:
                printDbg("DB: Getting rewards of all masternodes")
                cursor.execute("SELECT * FROM UTXOS")
            else:
                printDbg("DB: Getting rewards of %s" % receiver)
                cursor.execute("SELECT * FROM UTXOS WHERE receiver = ?", (receiver,))
            rows = cursor.fetchall()
        except Exception as e:
            err_msg = 'error getting rewards list for %s' % receiver
            printException(getCallerName(), getFunctionName(), err_msg, e)
            rows = []
        finally:
            self.releaseCursor()
        return self.rewards_from_rows(rows)

    """
    txes methods
    """

    def txes_from_rows(self, rows):
        txes = []
        for row in rows:
            tx = {}
            tx['txid'] = row[0]
            tx['rawtx'] = row[1]
            txes.append(tx)
        return txes

    def addRawTx(self, tx_hash, rawtx, lastfetch=0):
        logging.debug("DB: Adding rawtx for %s" % tx_hash)
        try:
            cursor = self.getCursor()
            cursor.execute("INSERT OR REPLACE INTO RAWTXES VALUES (?, ?, ?)", (tx_hash, rawtx, lastfetch))
        except Exception as e:
            err_msg = 'error adding rawtx to DB'
            printException(getCallerName(), getFunctionName(), err_msg, e)
        finally:
            self.releaseCursor()

    def deleteRawTx(self, tx_hash):
        logging.debug("DB: Deleting rawtx for %s" % tx_hash)
        try:
            cursor = self.getCursor()
            cursor.execute("DELETE FROM RAWTXES WHERE tx_hash = ?", (tx_hash,))
        except Exception as e:
            err_msg = 'error deleting rawtx from DB'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
        finally:
            self.releaseCursor(vacuum=True)

    def getRawTx(self, tx_hash):
        logging.debug("DB: Getting rawtx for %s" % tx_hash)
        try:
            cursor = self.getCursor()
            cursor.execute("SELECT * FROM RAWTXES WHERE tx_hash = ?", (tx_hash,))
            rows = cursor.fetchall()
        except Exception as e:
            err_msg = 'error getting raw tx for %s' % tx_hash
            printException(getCallerName(), getFunctionName(), err_msg, e)
            rows = []
        finally:
            self.releaseCursor()
        if rows:
            return self.txes_from_rows(rows)[0]
        return None

    def clearRawTxes(self, minTime):
        printDbg("Pruning table RAWTXES")
        try:
            cursor = self.getCursor()
            cursor.execute("DELETE FROM RAWTXES WHERE lastfetch < ?", (minTime,))
        except Exception as e:
            err_msg = 'error deleting rawtx from DB'
            printException(getCallerName(), getFunctionName(), err_msg, e.args)
        finally:
            self.releaseCursor(vacuum=True)
