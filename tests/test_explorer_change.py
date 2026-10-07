import os
import sys
import unittest
from unittest.mock import MagicMock

# The app runs with `src/` on sys.path (see pet4l.py), so its modules import
# each other flat (e.g. `from apiClient import ApiClient`). Mirror that here.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blockbookClient import BlockBookClient  # noqa: E402

# MainWindow pulls in the hardware-wallet stack (btchip/trezor), which may not
# be installed in a CI/headless environment. Import it lazily so the explorer
# fallback tests can still run on their own.
try:
    import mainWindow as mainWindow_mod  # noqa: E402
    from mainWindow import MainWindow  # noqa: E402
    MAINWINDOW_AVAILABLE = True
except Exception:
    MAINWINDOW_AVAILABLE = False


class FakeMainWnd:
    """Minimal stand-in for MainWindow as seen by BlockBookClient."""
    def __init__(self, urls):
        self.urls = urls

    def getExplorerURL(self, network):
        return self.urls[0]

    def getExplorerURLList(self, network):
        return list(self.urls)


class BlockBookFallbackTest(unittest.TestCase):
    def test_loads_primary_url(self):
        client = BlockBookClient(FakeMainWnd(['https://primary.example', 'https://zkbitcoin.com/']))
        self.assertEqual(client.url, 'https://primary.example')

    def test_fallback_excludes_current_url(self):
        client = BlockBookClient(FakeMainWnd(['https://primary.example', 'https://zkbitcoin.com/']))
        self.assertEqual(client.getFallbackUrls(), ['https://zkbitcoin.com/'])

    def test_retries_next_explorer_on_failure(self):
        # Primary fails -> the call must transparently retry on the next
        # configured explorer (e.g. zkbitcoin) and succeed.
        client = BlockBookClient(FakeMainWnd(['https://primary.example', 'https://zkbitcoin.com/']))
        attempted = []

        def fake_checkResponse(method, param=""):
            attempted.append(client.url)
            if client.url == 'https://primary.example':
                raise Exception("primary down")
            return [{'txid': 'abc'}]

        client.checkResponse = fake_checkResponse
        utxos = client.getAddressUtxos('myaddress')

        self.assertEqual(attempted, ['https://primary.example', 'https://zkbitcoin.com/'])
        self.assertEqual(client.url, 'https://zkbitcoin.com/')
        self.assertEqual(utxos[0]['script'], '')

    def test_raises_when_all_explorers_fail(self):
        client = BlockBookClient(FakeMainWnd(['https://primary.example', 'https://zkbitcoin.com/']))
        client.checkResponse = MagicMock(side_effect=Exception("everything down"))
        with self.assertRaises(Exception):
            client.getBalance('myaddress')
        # primary + every fallback was tried
        self.assertEqual(client.checkResponse.call_count, 2)


class FakeComboBox:
    """Just enough of QComboBox for the explorer methods under test."""
    def __init__(self, items=None):
        self._items = list(items or [])  # list of (text, data)
        self._index = 0 if self._items else -1

    def clear(self):
        self._items = []
        self._index = -1

    def addItem(self, text, data=None):
        self._items.append((text, data))
        if self._index < 0:
            self._index = 0

    def count(self):
        return len(self._items)

    def setCurrentIndex(self, i):
        self._index = i

    def currentIndex(self):
        return self._index

    def findText(self, text):
        for idx, (t, _) in enumerate(self._items):
            if t == text:
                return idx
        return -1

    def itemData(self, i):
        if 0 <= i < len(self._items):
            return self._items[i][1]
        return None

    def currentData(self):
        return self.itemData(self._index)


@unittest.skipUnless(MAINWINDOW_AVAILABLE, "MainWindow deps (btchip/trezor) unavailable")
class OnChangeSelectedExplorerTest(unittest.TestCase):
    def _make_window(self, items):
        # Bypass the heavy __init__; we only exercise onChangeSelectedExplorer.
        win = MainWindow.__new__(MainWindow)
        win.updatingExplorerbox = False
        win.isTestnetRPC = False
        win.parent = MagicMock()
        win.parent.cache = {'selectedExplorer_mainnet': '', 'selectedExplorer_testnet': ''}
        win.apiClient = MagicMock()
        win.header = MagicMock()
        win.header.explorerClientsBox = FakeComboBox(items)
        win.explorerServersList = [data for _, data in items]
        return win

    def setUp(self):
        self.items = [
            ("https://explorer1.com", {'id': 1, 'url': 'https://explorer1.com', 'isTestnet': False, 'isCustom': True}),
            ("https://explorer2.com", {'id': 2, 'url': 'https://explorer2.com', 'isTestnet': False, 'isCustom': True}),
        ]
        # Avoid touching real QSettings; just echo the value back.
        self._orig_persist = mainWindow_mod.persistCacheSetting
        mainWindow_mod.persistCacheSetting = lambda key, value: value

    def tearDown(self):
        mainWindow_mod.persistCacheSetting = self._orig_persist

    def test_change_updates_api_client(self):
        win = self._make_window(self.items)
        win.onChangeSelectedExplorer(1)
        win.apiClient.updateExplorerUrl.assert_called_with('https://explorer2.com')

    def test_change_persists_url_for_network(self):
        win = self._make_window(self.items)
        win.onChangeSelectedExplorer(1)
        self.assertEqual(win.parent.cache['selectedExplorer_mainnet'], 'https://explorer2.com')

    def test_guard_blocks_programmatic_change(self):
        win = self._make_window(self.items)
        win.updatingExplorerbox = True
        win.onChangeSelectedExplorer(1)
        win.apiClient.updateExplorerUrl.assert_not_called()


@unittest.skipUnless(MAINWINDOW_AVAILABLE, "MainWindow deps (btchip/trezor) unavailable")
class ExplorerPerNetworkSelectionTest(unittest.TestCase):
    """Selection must be remembered per network, not by a shared index."""
    ALL = [
        {'id': 1, 'url': 'https://m1', 'isTestnet': False, 'isCustom': False},
        {'id': 2, 'url': 'https://m2', 'isTestnet': False, 'isCustom': False},
        {'id': 3, 'url': 'https://t1', 'isTestnet': True, 'isCustom': False},
    ]

    def setUp(self):
        self._orig_persist = mainWindow_mod.persistCacheSetting
        mainWindow_mod.persistCacheSetting = lambda key, value: value
        self.win = MainWindow.__new__(MainWindow)
        self.win.updatingExplorerbox = False
        self.win.apiClient = MagicMock()
        self.win.header = MagicMock()
        self.win.header.explorerClientsBox = FakeComboBox()
        self.win.parent = MagicMock()
        self.win.parent.cache = {'selectedExplorer_mainnet': 'https://m1',
                                 'selectedExplorer_testnet': 'https://t1'}
        self.win.parent.db.getExplorerServers.return_value = self.ALL

    def tearDown(self):
        mainWindow_mod.persistCacheSetting = self._orig_persist

    def test_network_switch_does_not_inherit_index(self):
        # On mainnet, user picks the 2nd mainnet explorer (m2).
        self.win.isTestnetRPC = False
        self.win.updateExplorerList()
        self.win.onChangeSelectedExplorer(1)
        self.assertEqual(self.win.parent.cache['selectedExplorer_mainnet'], 'https://m2')

        # Switch to testnet: index 1 must NOT carry over; t1 is restored.
        self.win.isTestnetRPC = True
        self.win.updateExplorerList()
        self.assertEqual(self.win.header.explorerClientsBox.currentData()['url'], 'https://t1')
        self.win.apiClient.updateExplorerUrl.assert_called_with('https://t1')

        # Switch back to mainnet: the saved m2 choice is restored, not reset.
        self.win.isTestnetRPC = False
        self.win.updateExplorerList()
        self.assertEqual(self.win.header.explorerClientsBox.currentData()['url'], 'https://m2')


class InitTableExplorerTest(unittest.TestCase):
    """initTable_Explorer must seed defaults and repair upgraded databases."""
    def _run(self, setup_rows):
        import sqlite3
        from database import Database
        from constants import trusted_explorers, DEFAULT_MAINNET_EXPLORER, DEFAULT_TESTNET_EXPLORER
        self.DEFAULT_MAINNET_EXPLORER = DEFAULT_MAINNET_EXPLORER
        self.DEFAULT_TESTNET_EXPLORER = DEFAULT_TESTNET_EXPLORER
        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        cur.execute("CREATE TABLE EXPLORER_SERVERS"
                    " (id INTEGER PRIMARY KEY, url TEXT, isTestnet BOOLEAN, isCustom BOOLEAN)")
        for row in setup_rows:
            cur.execute("INSERT INTO EXPLORER_SERVERS (id,url,isTestnet,isCustom) VALUES (?,?,?,?)", row)
        Database(MagicMock()).initTable_Explorer(cur)
        cur.execute("SELECT url,isTestnet,isCustom FROM EXPLORER_SERVERS ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        self.trusted_urls = [u for u, _, _ in trusted_explorers]
        return {url: (isT, isC) for url, isT, isC in rows}

    def test_fresh_db_seeds_all_defaults(self):
        result = self._run([])
        for url in self.trusted_urls:
            self.assertIn(url, result)
        # the mainnet default is seeded as a non-custom mainnet row
        self.assertEqual(result[self.DEFAULT_MAINNET_EXPLORER], (0, 0))

    def test_backfills_null_metadata_on_upgrade(self):
        from constants import DEFAULT_TESTNET_EXPLORER
        result = self._run([
            (0, 'https://explorer.duddino.com/', None, None),
            (1, DEFAULT_TESTNET_EXPLORER, None, None),
        ])
        # NULL testnet flag must be repaired, not left to read as mainnet
        self.assertEqual(result[DEFAULT_TESTNET_EXPLORER], (1, 0))
        # a newly shipped default is added to an already-populated DB
        self.assertIn(self.DEFAULT_MAINNET_EXPLORER, result)

    def test_no_id_collision_with_existing_custom(self):
        result = self._run([
            (0, 'https://explorer.duddino.com/', 0, 0),
            (1, 'https://testnet.duddino.com/', 1, 0),
            (2, 'https://my.custom.explorer/', 0, 1),
        ])
        # a new default is still inserted despite a custom row already at id 2...
        self.assertIn(self.DEFAULT_MAINNET_EXPLORER, result)
        # ...and the user's custom row is left untouched
        self.assertEqual(result['https://my.custom.explorer/'], (0, 1))


@unittest.skipUnless(MAINWINDOW_AVAILABLE, "MainWindow deps (btchip/trezor) unavailable")
class ExplorerUrlListTest(unittest.TestCase):
    def _window(self, explorers):
        win = MainWindow.__new__(MainWindow)
        win.explorerServersList = explorers
        win.header = MagicMock()
        win.header.explorerClientsBox.currentData.return_value = None
        return win

    def test_filters_by_network(self):
        win = self._window([
            {'url': 'https://m1', 'isTestnet': False, 'isCustom': False},
            {'url': 'https://t1', 'isTestnet': True, 'isCustom': False},
            {'url': 'https://zk', 'isTestnet': False, 'isCustom': False},
        ])
        self.assertEqual(win.getExplorerURLList('mainnet'), ['https://m1', 'https://zk'])
        self.assertEqual(win.getExplorerURLList('testnet'), ['https://t1'])

    def test_defaults_when_network_empty(self):
        from constants import DEFAULT_MAINNET_EXPLORER, DEFAULT_TESTNET_EXPLORER
        win = self._window([])
        self.assertEqual(win.getExplorerURLList('mainnet'), [DEFAULT_MAINNET_EXPLORER])
        self.assertEqual(win.getExplorerURLList('testnet'), [DEFAULT_TESTNET_EXPLORER])

    def test_getExplorerURL_reads_cache_not_widget(self):
        win = MainWindow.__new__(MainWindow)
        win.explorerServersList = [
            {'url': 'https://m1', 'isTestnet': False, 'isCustom': False},
            {'url': 'https://m2', 'isTestnet': False, 'isCustom': False},
            {'url': 'https://t1', 'isTestnet': True, 'isCustom': False},
        ]
        win.parent = MagicMock()
        win.parent.cache = {'selectedExplorer_mainnet': 'https://m2',
                            'selectedExplorer_testnet': 'https://t1'}
        # No header: any Qt-widget access from this worker-thread-safe method
        # would raise AttributeError and fail the test.
        win.header = None
        self.assertEqual(win.getExplorerURL('mainnet'), 'https://m2')
        self.assertEqual(win.getExplorerURL('testnet'), 'https://t1')
        # A stale/removed saved URL falls back to the first for that network.
        win.parent.cache['selectedExplorer_mainnet'] = 'https://gone'
        self.assertEqual(win.getExplorerURL('mainnet'), 'https://m1')


class ExplorerTableMigrationTest(unittest.TestCase):
    """Covers the cleanup applied to EXPLORER_SERVERS on startup."""

    def _legacyDB(self):
        # Reproduce a DB created by the older schema: a leading 'is_custom'
        # column, duplicate rows and mixed trailing slashes.
        import sqlite3
        from constants import DEFAULT_TESTNET_EXPLORER
        path = os.path.join(self.tmp, 'application.db')
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE EXPLORER_SERVERS("
                     " id INTEGER PRIMARY KEY, url TEXT, is_custom BOOLEAN)")
        conn.executemany("INSERT INTO EXPLORER_SERVERS (id, url, is_custom) VALUES (?, ?, ?)",
                         [(1, DEFAULT_TESTNET_EXPLORER.rstrip('/'), None),
                          (2, DEFAULT_TESTNET_EXPLORER, None),
                          (3, 'https://dead-default.com/', None),
                          (4, 'https://mine.example', 1)])
        conn.commit()
        conn.close()
        return path

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.dbfile = self._legacyDB()
        import constants
        self._saved = constants.database_File
        constants.database_File = self.dbfile
        import database
        database.database_File = self.dbfile
        self.database = database

    def tearDown(self):
        import constants
        constants.database_File = self._saved
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _openDB(self):
        app = MagicMock()
        db = self.database.Database(app)
        db.file_name = self.dbfile
        db.openDB()
        return db

    def test_migration_cleans_and_preserves(self):
        db = self._openDB()
        rows = db.getExplorerServers()
        urls = [r['url'] for r in rows]

        # Trailing-slash duplicates collapse into one canonical entry...
        from constants import DEFAULT_TESTNET_EXPLORER
        self.assertEqual(urls.count(DEFAULT_TESTNET_EXPLORER), 1)
        # ...defaults no longer shipped are pruned...
        self.assertNotIn('https://dead-default.com/', urls)
        # ...but a user's custom explorer survives, still flagged custom.
        mine = [r for r in rows if r['url'] == 'https://mine.example/']
        self.assertEqual(len(mine), 1)
        self.assertTrue(mine[0]['isCustom'])
        db.close()

    def test_flags_not_shifted_by_legacy_column(self):
        # The legacy 'is_custom' column must not be read as isTestnet:
        # the testnet default has to come back with isTestnet set.
        from constants import DEFAULT_TESTNET_EXPLORER
        db = self._openDB()
        row = [r for r in db.getExplorerServers()
               if r['url'] == DEFAULT_TESTNET_EXPLORER][0]
        self.assertTrue(row['isTestnet'])
        self.assertEqual([r['url'] for r in db.getExplorerServers(isTestnet=True)],
                         [DEFAULT_TESTNET_EXPLORER])
        db.close()

    def test_duplicate_adds_are_ignored(self):
        db = self._openDB()
        before = len(db.getExplorerServers())
        db.addExplorerServer('https://new.example', False)
        db.addExplorerServer('https://new.example/', False)   # same URL
        self.assertEqual(len(db.getExplorerServers()), before + 1)
        db.close()


class TimeThisTest(unittest.TestCase):
    def test_returns_value_and_elapsed(self):
        # Regression: this used time.clock(), removed in Python 3.8, so every
        # call returned (None, None) and a healthy RPC server was reported
        # as unreachable.
        from misc import timeThis
        value, elapsed = timeThis(lambda x: x * 2, 21)
        self.assertEqual(value, 42)
        self.assertIsNotNone(elapsed)

    def test_failure_still_returns_none(self):
        from misc import timeThis

        def boom():
            raise RuntimeError("nope")
        self.assertEqual(timeThis(boom), (None, None))


if __name__ == '__main__':
    unittest.main()
