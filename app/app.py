from flask import Flask, render_template, request, redirect, url_for, session, flash
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
        username = request.form['username']
        password = request.form['password']

        server = Server(LDAP_SERVER, get_info=ALL)

        try:
            conn = Connection(server)
            if not conn.bind():
                return render_template('login.html', error="Anonymous bind failed."), 500

            search_base = LDAP_BASE_DN
            search_filter = f"(uid={username})"
            conn.search(search_base, search_filter, attributes=["mail", "entryDN"])

            if not conn.entries:
                return render_template('login.html', error="User not found."), 404

            user_entry = conn.entries[0]
            user_dn = str(user_entry.entry_dn)
            user_email = str(user_entry.mail) if hasattr(user_entry, "mail") else None

            if not user_email:
                return render_template('login.html', error="Email not found in LDAP entry."), 404

            conn.unbind()

            user_conn = Connection(server, user=user_dn, password=password)
            if user_conn.bind():
                session['user_email'] = user_email
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid LDAP credentials"), 403
        except Exception as e:
            return render_template('login.html', error=f"LDAP authentication failed: {e}"), 500

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
    admin_emails = [email.strip() for email in admin_emails]

    user_email = session['user_email']
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    data = {}
    row_counter = 0
    for (table_name,) in tables:
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        columns = [col[0] for col in cursor.fetchall()]

        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        visible_rows = []
        for row in rows:
            owner, watchers = row[5], row[6]
            if user_email in (owner or '') or user_email in (watchers or '') or user_email in admin_emails:
                row_counter += 1
                visible_rows.append((row_counter,) + row[1:])  # Add row counter and exclude id

        if visible_rows:
            data[table_name] = {"columns": ['No'] + columns[1:], "rows": visible_rows}

    connection.close()
    return render_template('dashboard.html', tables=data)

@app.route('/manage', methods=['GET', 'POST'])
def manage():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    admin_emails = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')
    admin_emails = [email.strip().lower() for email in admin_emails]
    user_email = session['user_email'].strip().lower()

    if user_email not in admin_emails:
        return "You do not have permission to access this page.", 403

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
                insert_date DATE DEFAULT CURRENT_DATE,
                dom DATE DEFAULT CURRENT_DATE,
                exp_date DATE NOT NULL,
                owner TEXT NOT NULL,
                watchers TEXT,
                comment TEXT
            )
            """
            cursor.execute(query)
            connection.commit()
            send_email(
                "New Table Created",
                f"Table '{table_name}' has been created by {user_email}.",
                admin_emails
            )
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
            INSERT INTO {table_name} (name, insert_date, exp_date, owner, watchers, comment)
            VALUES (%s, CURRENT_DATE, %s, %s, %s, %s)
            """
            cursor.execute(query, (name, exp_date, owner, watchers, comment))
            connection.commit()

            all_emails = set([owner] + watchers.split(", ") + admin_emails)
            send_email(
                "New Row Added",
                f"Row '{name}' has been added to table '{table_name}'.",
                all_emails
            )
        elif action == 'delete_table':
            cursor.execute(f"DROP TABLE {table_name}")
            connection.commit()
            send_email(
                "Table Deleted",
                f"Table '{table_name}' has been deleted by {user_email}.",
                admin_emails
            )
        elif action == 'delete_row':
            row_name = request.form['row_name']
            cursor.execute(f"DELETE FROM {table_name} WHERE name = %s", (row_name,))
            connection.commit()
            send_email(
                "Row Deleted",
                f"Row '{row_name}' in table '{table_name}' has been deleted by {user_email}.",
                admin_emails
            )

    connection.close()
    return render_template('manage.html')

@app.route('/modify', methods=['GET', 'POST'])
def modify():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    admin_emails = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')
    admin_emails = [email.strip() for email in admin_emails]

    user_email = session['user_email']

    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        table_name = request.form.get('table_name')
        row_name = request.form.get('row_name')

        if not table_name or not row_name:
            connection.close()
            return "Table name and row name are required.", 400

        query = f"SELECT * FROM {table_name} WHERE name = %s"
        cursor.execute(query, (row_name,))
        row = cursor.fetchone()

        if not row:
            connection.close()
            return "Row not found.", 404

        old_owner = row[5]
        old_watchers = row[6] if row[6] else ''
        old_watchers_list = old_watchers.split(", ")

        old_exp_date = str(row[4])
        old_comment = row[7]

        owner_emails = [email.strip() for email in old_owner.split(",")]

        if user_email not in admin_emails and user_email not in owner_emails:
            connection.close()
            return "You do not have permission to modify this row.", 403

        updates = []
        params = []
        changes = []

        new_exp_date = request.form.get('new_exp_date')
        if new_exp_date and new_exp_date != old_exp_date:
            updates.append("exp_date = %s")
            params.append(new_exp_date)
            changes.append(f"  - Expiration Date: '{old_exp_date}' -> '{new_exp_date}'")

        new_comment = request.form.get('new_comment')
        if new_comment and new_comment != old_comment:
            updates.append("comment = %s")
            params.append(new_comment)
            changes.append(f"  - Comment: '{old_comment}' -> '{new_comment}'")

        new_owner = request.form.get('new_owner')
        if new_owner and new_owner != old_owner:
            updates.append("owner = %s")
            params.append(new_owner)
            changes.append(f"  - Owner: '{old_owner}' -> '{new_owner}'")

        new_watchers = request.form.get('new_watchers')
        if new_watchers and new_watchers != old_watchers:
            updates.append("watchers = %s")
            params.append(new_watchers)
            changes.append(f"  - Watchers: '{old_watchers}' -> '{new_watchers}'")

        if updates:
            updates.append("dom = CURRENT_DATE")
            query = f"UPDATE {table_name} SET {', '.join(updates)} WHERE name = %s"
            params.append(row_name)
            cursor.execute(query, tuple(params))
            connection.commit()

            all_emails = set([old_owner] + old_watchers_list + [new_owner] + new_watchers.split(", ") + admin_emails)
            send_email(
                "Row Updated",
                f"The row '{row_name}' in table '{table_name}' has been updated.\nChanges:\n" + "\n".join(changes),
                all_emails
            )

    connection.close()
    return render_template('modify.html', success=True)

@app.route('/admin')
def admin_panel():
    admin_emails = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')
    admin_emails = [email.strip() for email in admin_emails]

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
