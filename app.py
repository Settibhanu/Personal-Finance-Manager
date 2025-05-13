from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = '123'  # Needed for session management

DB_NAME = os.path.join(app.instance_path, 'finance.db')

# Create tables if they don't exist
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()

        # Create users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # Create accounts table (bank accounts)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bank_name TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Create transactions table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id INTEGER,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        ''')

        conn.commit()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE user_id = ?", (session['user_id'],))
        transactions = cur.fetchall()
        income = sum(t[3] for t in transactions if t[2] == 'income')
        expenses = sum(t[3] for t in transactions if t[2] == 'expense')
        balance = income - expenses

    return render_template('index.html', transactions=transactions, income=income, expenses=expenses, balance=balance)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        bank_name = request.form['bank_name']
        initial_balance = float(request.form['initial_balance'])

        try:
            # Insert user into the users table
            with sqlite3.connect(DB_NAME) as conn:
                cur = conn.cursor()

                # Add the user
                cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()

                # Get the newly inserted user id
                cur.execute("SELECT id FROM users WHERE username = ?", (username,))
                user_id = cur.fetchone()[0]

                # Add bank account for the user
                cur.execute("INSERT INTO accounts (user_id, bank_name, balance) VALUES (?, ?, ?)", 
                            (user_id, bank_name, initial_balance))
                conn.commit()

                flash("Registration successful, please log in.")
                return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.")
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
            user = cur.fetchone()
            if user:
                session['user_id'] = user[0]
                session['username'] = username
                return redirect(url_for('index'))
            else:
                flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE user_id = ?", (session['user_id'],))
        accounts = cur.fetchall()

    if request.method == 'POST':
        t_type = request.form['type']
        amount = float(request.form['amount'])
        category = request.form['category']
        description = request.form['description']
        account_id = request.form['account']

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            # Add transaction to the transactions table
            cur.execute('''
                INSERT INTO transactions (user_id, account_id, type, amount, category, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], account_id, t_type, amount, category, description))

            # Update account balance based on transaction type
            if t_type == 'income':
                cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
            elif t_type == 'expense':
                cur.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))

            conn.commit()

        return redirect(url_for('index'))

    return render_template('add_transaction.html', accounts=accounts)

@app.route('/add_account', methods=['POST'])
def add_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    bank_name = request.form['bank_name']
    initial_balance = float(request.form['initial_balance'])

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO accounts (user_id, bank_name, balance)
            VALUES (?, ?, ?)
        ''', (session['user_id'], bank_name, initial_balance))
        conn.commit()

    flash('Bank account added successfully.')
    return redirect(url_for('index'))

@app.route('/bank_balance')
def bank_balance():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE user_id = ?", (session['user_id'],))
        accounts = cur.fetchall()

    return render_template('bank_balance.html', accounts=accounts)

@app.route('/delete/<int:id>')
def delete_transaction(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (id, session['user_id']))
        conn.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
