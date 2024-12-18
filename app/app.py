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
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
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

    admin_emails = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')
    admin_emails = [email.strip() for email in admin_emails]  # Processed as a list in Python

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    data = {}
    for (table_name,) in tables:
        cursor.execute(f"SELECT * FROM {table_name}")
        data[table_name] = cursor.fetchall()
    connection.close()
    return render_template('dashboard.html', tables=data, admin_emails=admin_emails)


@app.route('/manage', methods=['GET', 'POST'])
def manage():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        action = request.form['action']
        table_name = request.form['table_name']

        if action == 'create':
            query = f"""
            CREATE TABLE {table_name} (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL,
                exp_date DATE NOT NULL,
                owner VARCHAR(255) NOT NULL,
                watchers TEXT,
                comment TEXT
            )
            """
            cursor.execute(query)
            connection.commit()
        elif action == 'add_row':
            name = request.form['name']
            exp_date = request.form['exp_date']
            owner = request.form['owner']
            watchers = request.form['watchers']
            comment = request.form['comment']

            if not is_valid_email(owner):
                connection.close()
                return "Invalid owner email.", 400

            query = f"""
            INSERT INTO {table_name} (name, exp_date, owner, watchers, comment)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (name, exp_date, owner, watchers, comment))
            connection.commit()

    connection.close()
    return render_template('manage.html')

@app.route('/modify', methods=['GET', 'POST'])
def modify():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    # Fetch the admin list
    admin_emails = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')
    admin_emails = [email.strip() for email in admin_emails]

    user_email = session['user_email']
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        # Retrieve form data
        table_name = request.form.get('table_name')
        row_name = request.form.get('row_name')

        if not table_name or not row_name:
            connection.close()
            return "Table name and row name are required.", 400

        # Fetch the row to be modified
        query = f"SELECT * FROM {table_name} WHERE name = %s"
        cursor.execute(query, (row_name,))
        row = cursor.fetchone()
        if not row:
            connection.close()
            return "Row not found.", 404

        # Get existing data
        old_owner, old_watchers, old_exp_date, old_comment = row[4], row[5], row[2], row[6]
        old_watchers_list = old_watchers.split(", ") if old_watchers else []

        # Check permissions
        if user_email not in admin_emails and user_email != old_owner:
            connection.close()
            return "You do not have permission to modify this row.", 403

        # Columns to update
        updates = []
        params = []
        changes = []

        # Handle expiration date
        new_exp_date = request.form.get('new_exp_date')
        if new_exp_date and new_exp_date != str(old_exp_date):
            updates.append("exp_date = %s")
            params.append(new_exp_date)
            changes.append(f"  - Expiration Date: '{old_exp_date}' -> '{new_exp_date}'")

        # Handle comment
        new_comment = request.form.get('new_comment')
        if new_comment and new_comment != old_comment:
            updates.append("comment = %s")
            params.append(new_comment)
            changes.append(f"  - Comment: '{old_comment}' -> '{new_comment}'")

        # Handle owner
        new_owner = request.form.get('new_owner')
        if new_owner and new_owner != old_owner:
            updates.append("owner = %s")
            params.append(new_owner)
            changes.append(f"  - Owner: '{old_owner}' -> '{new_owner}'")

        # Handle watchers
        new_watchers = request.form.get('new_watchers')
        new_watchers_list = new_watchers.split(", ") if new_watchers else []
        if new_watchers and new_watchers != old_watchers:
            updates.append("watchers = %s")
            params.append(new_watchers)
            changes.append(f"  - Watchers: '{old_watchers}' -> '{new_watchers}'")

        # Admin-only changes: Modify table name and row name
        if user_email in admin_emails:
            new_table_name = request.form.get('new_table_name')
            new_row_name = request.form.get('new_row_name')

            if new_table_name and new_table_name != table_name:
                changes.append(f"  - Table Name: '{table_name}' -> '{new_table_name}'")
                table_name = new_table_name

            if new_row_name and new_row_name != row_name:
                updates.append("name = %s")
                params.append(new_row_name)
                changes.append(f"  - Row Name: '{row_name}' -> '{new_row_name}'")
                row_name = new_row_name

        # Update the database
        if updates:
            updates.append("dom = CURRENT_TIMESTAMP")  # Update the "date of modification"
            query = f"UPDATE {table_name} SET {', '.join(updates)} WHERE name = %s"
            params.append(row_name)
            cursor.execute(query, tuple(params))
            connection.commit()

            # Notify old and new participants
            all_emails = set([old_owner] + old_watchers_list + [new_owner] + new_watchers_list)
            send_email(
                "Row Updated",
                f"The row '{row_name}' in table '{table_name}' has been updated.\nChanges:\n" + "\n".join(changes),
                all_emails
            )

    connection.close()
    return render_template('modify.html', success=True)



@app.route('/admin')
def admin_panel():
    # Get comma-separated list of admin emails from environment
    admin_emails = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')

    # Strip whitespace from each email
    admin_emails = [email.strip() for email in admin_emails]

    # Check if user is authenticated and is in the admin list
    if 'user_email' not in session or session['user_email'] not in admin_emails:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    data = {}
    for (table_name,) in tables:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        columns = [col[0] for col in cursor.fetchall()]
        data[table_name] = {"columns": columns, "rows": rows}
    connection.close()
    return render_template('admin.html', tables=data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
