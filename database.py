import sqlite3
from datetime import datetime

class Database:
    def __init__(self, database_path):
        self.conn = sqlite3.connect(database_path, check_same_thread=False)
        self.create_tables()

    # In the create_tables method, update the users table:
    def create_tables(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT DEFAULT '',  
            task_balance INTEGER DEFAULT 500,
            affiliate_balance INTEGER DEFAULT 0,
            token TEXT,
            account_number TEXT,
            account_name TEXT, 
            bank_name TEXT,
            completed_task INTEGER DEFAULT 0,
            last_task_completed TEXT DEFAULT NULL,
            task_picture TEXT DEFAULT NULL,
            task_picture_timestamp TIMESTAMP DEFAULT NULL,
            referral_link TEXT DEFAULT ''
        )''')
       
        self.conn.execute('''CREATE TABLE IF NOT EXISTS current_task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT,
            instructions TEXT
        )''')

        self.conn.execute('''CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id)
         )''')
        
        self.conn.execute('''CREATE TABLE IF NOT EXISTS user_pins (
            chat_id INTEGER PRIMARY KEY,
            pin TEXT NOT NULL
        )''')
        
        self.conn.execute('''CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            used INTEGER DEFAULT 0
        )''')
    
        
        self.conn.execute('''CREATE TABLE IF NOT EXISTS withdrawal_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            withdrawal_amount INTEGER,
            status TEXT DEFAULT 'Succesful',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id)
        )''')

        self.conn.execute('''CREATE TABLE IF NOT EXISTS referrals (
            referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users(id),
            FOREIGN KEY (referred_id) REFERENCES users(id)
        )''')

        cursor = self.conn.cursor()
        cursor.execute('PRAGMA table_info(users)')
        columns = [column[1] for column in cursor.fetchall()]
        if 'last_name' not in columns:
            self.conn.execute('ALTER TABLE users ADD COLUMN last_name TEXT DEFAULT ""')
        if 'completed_task' not in columns:
            self.conn.execute('''ALTER TABLE users ADD COLUMN completed_task INTEGER DEFAULT 0''')
        if 'task_picture' not in columns:
            self.conn.execute('ALTER TABLE users ADD COLUMN task_picture TEXT DEFAULT NULL')
        if 'task_status' not in columns:
            self.conn.execute('ALTER TABLE users ADD COLUMN task_status TEXT DEFAULT NULL')
        if 'task_picture_timestamp' not in columns:
            self.conn.execute('ALTER TABLE users ADD COLUMN task_picture_timestamp TIMESTAMP DEFAULT NULL')
        if 'referral_link' not in columns:
            self.conn.execute('ALTER TABLE users ADD COLUMN referral_link TEXT DEFAULT ""')
        
    def save_tokens(self, tokens):
        with self.conn:
            self.conn.executemany('INSERT INTO tokens (token) VALUES (?)', [(token,) for token in tokens])

    def get_unused_tokens(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT token FROM tokens WHERE used = 0')
        return [row[0] for row in cursor.fetchall()]

    def is_token_used(self, token):
        cursor = self.conn.cursor()
        cursor.execute('SELECT used FROM tokens WHERE token = ?', (token,))
        result = cursor.fetchone()
        return result and result[0] == 1
    
    def get_top_referrers(self, limit=10):
        cursor = self.conn.cursor()
        query = """
        SELECT referrer_id, COUNT(referral_id) AS referral_count
        FROM referrals
        GROUP BY referrer_id
        ORDER BY referral_count DESC
        LIMIT ?
        """
        cursor.execute(query, (limit,))
        return cursor.fetchall()
    
    def mark_token_as_used(self, token):
        with self.conn:
            self.conn.execute('UPDATE tokens SET used = 1 WHERE token = ?', (token,))

    def save_pin(self, chat_id, pin):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO user_pins (chat_id, pin) VALUES (?, ?)", (chat_id, pin))

    def get_pin(self, chat_id):
        with self.conn:
            result = self.conn.execute("SELECT pin FROM user_pins WHERE chat_id = ?", (chat_id,)).fetchone()
            return result[0] if result else None

    def update_pin(self, chat_id, new_pin):
        with self.conn:
            self.conn.execute("UPDATE user_pins SET pin = ? WHERE chat_id = ?", (new_pin, chat_id))
    
    def verify_pin(self, chat_id, pin):
        result = self.conn.execute('SELECT pin FROM user_pins WHERE chat_id = ? AND pin = ?', (chat_id, pin))
        return result.fetchone() is not None

    def is_pin_set(self, chat_id):
        return self.get_pin(chat_id) is not None

    def is_user_registered(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT chat_id FROM users WHERE chat_id = ?', (chat_id,))
        return cursor.fetchone() is not None

    def register_user(self, chat_id, first_name, token):
        with self.conn:
            self.conn.execute('INSERT INTO users (chat_id, first_name, token) VALUES (?, ?, ?)', (chat_id, first_name, token))

    def get_user_balances(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT task_balance, affiliate_balance FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        return {'task_balance': result[0], 'affiliate_balance': result[1]} if result else {'task_balance': 0, 'affiliate_balance': 0}

    def update_task_balance(self, chat_id, amount):
        with self.conn:
            self.conn.execute('UPDATE users SET task_balance = task_balance + ? WHERE chat_id = ?', (amount, chat_id))

    def update_affiliate_balance(self, chat_id, amount):
        with self.conn:
            self.conn.execute('UPDATE users SET affiliate_balance = affiliate_balance + ? WHERE chat_id = ?', (amount, chat_id))


    def save_account_details(self, chat_id, account_number, account_name, bank_name):
        with self.conn:
            self.conn.execute('UPDATE users SET account_number = ?, account_name = ?, bank_name = ? WHERE chat_id = ?', (account_number, account_name, bank_name, chat_id))

    def get_withdrawal_requests_by_user(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM withdrawal_requests WHERE chat_id = ?', (chat_id,))
        withdrawals = cursor.fetchall()

        return [{'withdrawal_amount': row[2], 'status': row[3], 'timestamp': row[4]} for row in withdrawals]

    def get_account_details(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT account_number, account_name, bank_name FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        if result and all(result):  # Check if all fields have values
            return ", ".join(str(field) for field in result)
        return None

    
    def store_withdrawal_request(self, chat_id, withdrawal_amount):
        with self.conn:
            self.conn.execute('INSERT INTO withdrawal_requests (chat_id, withdrawal_amount) VALUES (?, ?)', (chat_id, withdrawal_amount))

    def get_withdrawal_requests(self, status=None):
        cursor = self.conn.cursor()
        if status:
            cursor.execute('SELECT * FROM withdrawal_requests WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT * FROM withdrawal_requests')
        return cursor.fetchall()

    def update_withdrawal_request_status(self, request_id, new_status):
        with self.conn:
            self.conn.execute('UPDATE withdrawal_requests SET status = ? WHERE request_id = ?', (new_status, request_id))

    def approve_withdrawal_request(self, request_id):
        # Retrieve request details
        cursor = self.conn.cursor()
        cursor.execute('SELECT chat_id, withdrawal_amount FROM withdrawal_requests WHERE request_id = ?', (request_id,))
        result = cursor.fetchone()
        
        if result:
            chat_id, withdrawal_amount = result
            # Check user balance and update
            cursor.execute('SELECT balance FROM users WHERE chat_id = ?', (chat_id,))
            user_balance = cursor.fetchone()[0]
            if user_balance >= withdrawal_amount:
                # Update user balance
                self.conn.execute('UPDATE users SET balance = balance - ? WHERE chat_id = ?', (withdrawal_amount, chat_id))
                # Mark request as approved
                self.update_withdrawal_request_status(request_id, 'Approved')
                return True
            else:
                self.update_withdrawal_request_status(request_id, 'Rejected (Insufficient Balance)')
                return False
        else:
            return False

    def reject_withdrawal_request(self, request_id, reason):
        with self.conn:
            self.conn.execute('UPDATE withdrawal_requests SET status = ? WHERE request_id = ?', (f'Rejected: {reason}', request_id))
    
    def get_referral_count(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (chat_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def has_completed_task(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT completed_task FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        return result and result[0] == 1

    
    def record_referral(self, referrer_id, referred_id):
        with self.conn:
            self.conn.execute('INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)', (referrer_id, referred_id))
    
    def get_last_task_completed(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT last_task_completed FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        return datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S') if result and result[0] else None
    
    def mark_task_as_completed(self, chat_id):
        with self.conn:
            self.conn.execute('UPDATE users SET completed_task = 1, last_task_completed = ? WHERE chat_id = ?', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), chat_id))
    
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT chat_id FROM users')
        return [row[0] for row in cursor.fetchall()]

    def get_user_count(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        return cursor.fetchone()[0]
    
    def get_games_played_today(self, chat_id):
        today = datetime.now().date()
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM game_history 
            WHERE chat_id = ? AND DATE(played_at) = DATE(?)
        ''', (chat_id, today))
        return cursor.fetchone()[0]

    def increment_games_played_today(self, chat_id):
        with self.conn:
            self.conn.execute('''
                INSERT INTO game_history (chat_id, played_at)
                VALUES (?, CURRENT_TIMESTAMP)
            ''', (chat_id,))

    def save_task_picture(self, chat_id, file_id):
        timestamp = datetime.now()
        with self.conn:
            self.conn.execute('UPDATE users SET task_picture = ?, task_picture_timestamp = ? WHERE chat_id = ?', (file_id, timestamp, chat_id))


    def get_task_picture(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT task_picture FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_user_proofs(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT chat_id, task_picture, task_picture_timestamp FROM users WHERE task_picture IS NOT NULL')
        return [{'chat_id': row[0], 'file_id': row[1], 'timestamp': row[2]} for row in cursor.fetchall()]

    def save_current_task(self, image_id, instructions):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS current_task
                (id INTEGER PRIMARY KEY, image_id TEXT, instructions TEXT)''')
            self.conn.execute('DELETE FROM current_task')
            self.conn.execute('INSERT INTO current_task (image_id, instructions) VALUES (?, ?)',
                            (image_id, instructions))

    def get_current_task(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT image_id, instructions FROM current_task LIMIT 1')
        result = cursor.fetchone()
        if result:
            return {'image': result[0], 'instructions': result[1]}
        return None

    def update_user_task_status(self, chat_id, status):
        with self.conn:
            self.conn.execute('UPDATE users SET task_status = ? WHERE chat_id = ?', (status, chat_id))
    
    def clear_user_proofs(self):
        with self.conn:
            self.conn.execute('UPDATE users SET task_picture = NULL, task_picture_timestamp = NULL WHERE task_picture IS NOT NULL')
        
    def get_user_info(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT chat_id, first_name, last_name, task_balance, affiliate_balance, completed_task, referral_link FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        if result:
            return {
                'chat_id': result[0],
                'first_name': result[1],
                'last_name': result[2],
                'task_balance': result[3],
                'affiliate_balance': result[4],
                'completed_task': result[5],
                'referral_link': result[6]
            }
        return None