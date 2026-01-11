from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)
DB_NAME = 'cash_collection.db'

# Google Configuration
GOOGLE_CLIENT_ID = "5546206720-7aifk56mfqrk5pogp5p1nrge87uteg51.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- Authentication Routes ---
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        # Default role for new users is 'agent'
        role = 'agent'
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, mobile, username, password, role) VALUES (?, ?, ?, ?, ?)',
                         (name, mobile, username, hashed_password, role))
            conn.commit()
            flash('Registration successful! Please sign in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'error')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html', google_client_id=GOOGLE_CLIENT_ID)

@app.route('/forgot_password')
def forgot_password():
    flash('Password reset link has been sent to your registered mobile.', 'success')
    return redirect(url_for('login'))

from google.oauth2 import id_token
from google.auth.transport import requests

# ... (Previous code)

@app.route('/google_auth', methods=['POST'])
def google_auth():
    # Get the token via POST from Google
    token = request.form.get('credential')
    
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        user_email = idinfo['email']
        user_name = idinfo.get('name', user_email.split('@')[0])
        
        conn = get_db_connection()
        # Check if user exists
        user = conn.execute('SELECT * FROM users WHERE username = ?', (user_email,)).fetchone()
        
        if not user:
            # Create new Google User
            try:
                conn.execute('INSERT INTO users (name, mobile, username, password, role) VALUES (?, ?, ?, ?, ?)',
                             (user_name, '0000000000', user_email, 'google_auth', 'agent'))
                conn.commit()
                flash('Google Account connected! Logging in...', 'success')
                user = conn.execute('SELECT * FROM users WHERE username = ?', (user_email,)).fetchone()
            except sqlite3.IntegrityError:
                flash('Error creating account.', 'error')
                return redirect(url_for('login'))
                
        conn.close()
        
        # Login
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            return redirect(url_for('dashboard'))

    except ValueError:
        flash('Invalid Google token', 'error')
    
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Main Feature Routes ---

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        # Quick Add Collection
        amount = request.form['amount']
        purpose = request.form['purpose']
        date = request.form['date']
        user_id = session['user_id']
        conn.execute('INSERT INTO collections (user_id, date, amount, purpose) VALUES (?, ?, ?, ?)',
                     (user_id, date, amount, purpose))
        conn.commit()
        flash('Collection added!', 'success')
        return redirect(url_for('dashboard'))
    
    collections = conn.execute('SELECT * FROM collections WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 5', 
                               (session['user_id'],)).fetchall()
    total_amount = conn.execute('SELECT SUM(amount) FROM collections WHERE user_id = ?', (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    
    return render_template('dashboard.html', collections=collections, total=total_amount, collection_date=datetime.today().strftime('%Y-%m-%d'))

@app.route('/collection')
def collection():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    collections = conn.execute('SELECT * FROM collections WHERE user_id = ? ORDER BY date DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('collection.html', collections=collections)

@app.route('/monthly')
def monthly():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('monthly.html') # Placeholder for monthly interest logic

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        address = request.form['address']
        conn.execute('INSERT INTO customers (name, mobile, address) VALUES (?, ?, ?)', (name, mobile, address))
        conn.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))
        
    customers = conn.execute('SELECT * FROM customers ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('customers.html', customers=customers)

@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        amount = request.form['amount']
        purpose = request.form['purpose']
        date = request.form['date']
        conn.execute('INSERT INTO expenses (user_id, date, amount, purpose) VALUES (?, ?, ?, ?)', 
                     (session['user_id'], date, amount, purpose))
        conn.commit()
        flash('Expense recorded!', 'success')
        return redirect(url_for('expenses'))
        
    expenses = conn.execute('SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('expenses.html', expenses=expenses)

@app.route('/investment')
def investment():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('investment.html')

@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('reports.html')

@app.route('/cashout')
def cashout():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('cashout.html')

if __name__ == '__main__':
    app.run(debug=True)
