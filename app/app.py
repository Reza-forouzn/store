from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ldap3 import Server, Connection, ALL
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a_default_fallback_key')

# LDAP Server settings
LDAP_SERVER = os.environ.get('LDAP_SERVER', 'ldap://your-ldap-server')
LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN', 'dc=example,dc=com')

# Database connection settings
def get_db_connection():
    return mysql.connector.connect(
        user=os.environ.get('DB_USER', 'store'),
        password=os.environ.get('DB_PASSWORD', 'store'),
        host=os.environ.get('DB_HOST', '127.0.0.1'),
        database=os.environ.get('DB_NAME', 'store'),
        collation=os.environ.get('DB_COLLATION', 'utf8mb4_unicode_ci'),
        charset=os.environ.get('DB_CHARSET', 'utf8mb4'),
    )

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def send_email(subject, body, receiver_emails):
    port = int(os.environ.get('SMTP_PORT', 587))
    smtp_server = os.environ.get('SMTP_SERVER', 'mail')
    sender_email = os.environ.get('SMTP_EMAIL', 'email')
    password = os.environ.get('SMTP_PASSWORD', 'pass')

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            for email in receiver_emails:
                msg["To"] = email
                server.sendmail(sender_email, email, msg.as_string())
                print(f"Email sent to {email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # Get username without domain
        password = request.form['password']

        # Authenticate user with LDAP
        server = Server(LDAP_SERVER, get_info=ALL)
        user_dn = f"uid={username},{LDAP_BASE_DN}"

        try:
            # Step 1: Anonymous bind to search for DN
            conn = Connection(server)
            if not conn.bind():
                return "Anonymous bind failed.", 500

            search_base = LDAP_BASE_DN
            search_filter = f"(uid={username})"  # Adjust attribute (e.g., sAMAccountName)
            conn.search(search_base, search_filter)
            if not conn.entries:
                return "User not found.", 404

            # Extract DN
            user_dn = conn.entries[0].entry_dn
            conn.unbind()

            # Step 2: Bind with user's DN and password
            user_conn = Connection(server, user=user_dn, password=password)
            if user_conn.bind():
                session['user_email'] = f"{username}@example.com"
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid LDAP credentials")
        except Exception as e:
            return render_template('login.html', error=f"LDAP authentication failed: {e}")

    # If GET request, show the login form
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    data = {}
    for (table_name,) in tables:
        cursor.execute(f"SELECT * FROM {table_name}")
        data[table_name] = cursor.fetchall()
    connection.close()
    return render_template('dashboard.html', tables=data)

@app.route('/modify', methods=['GET', 'POST'])
def modify():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    user_email = session['user_email']  # Get authenticated user's email
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        table_name = request.form.get('table_name')
        row_name = request.form.get('row_name')

        if not table_name or not row_name:
            connection.close()
            return "Table name and row name are required.", 400

        # Check ownership
        query = f"SELECT * FROM {table_name} WHERE name = %s"
        cursor.execute(query, (row_name,))
        row = cursor.fetchone()
        if not row:
            connection.close()
            return "Row not found.", 404

        owner = row[4]  # Assuming 'owner' is in the 5th column
        if user_email != owner:
            connection.close()
            return "You do not have permission to modify this row.", 403


        connection.close()
        return render_template('modify.html', success=True)

    connection.close()
    return render_template('modify.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

