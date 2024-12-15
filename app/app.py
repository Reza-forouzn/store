from flask import Flask, render_template, request, jsonify
import mysql.connector
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Database connection settings
def get_db_connection():
    return mysql.connector.connect(
        user="store",
        password="store",
        host="192.168.5.38",
        database="store",
        collation="utf8mb4_unicode_ci",
        charset="utf8mb4",
    )

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def is_valid_date(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def send_email(subject, body, receiver_email):
    port = 587
    smtp_server = "mail."
    sender_email = "address@address"
    password = "pass"

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"Email sent to {receiver_email}")
    except Exception as e:
        print(f"Failed to send email to {receiver_email}: {e}")

@app.route('/')
def dashboard():
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

@app.route('/manage', methods=['GET', 'POST'])
def manage():
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        table_name = request.form['table_name']
        action = request.form['action']

        if action == 'create':
            query = f"""CREATE TABLE {table_name} (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL,
                insert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                dom TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exp_date DATE NOT NULL,
                owner VARCHAR(255) NOT NULL,
                watchers VARCHAR(1000),
                comment VARCHAR(1000)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"""
            cursor.execute(query)
        elif action == 'add_row':
            name = request.form['name']
            exp_date = request.form['exp_date']
            owner = request.form['owner']
            watchers = request.form['watchers']
            comment = request.form['comment']

            if not is_valid_date(exp_date):
                return "Invalid expiration date format.", 400

            if not is_valid_email(owner):
                return "Invalid owner email format.", 400

            watcher_list = [email.strip() for email in watchers.split(",")]
            for watcher in watcher_list:
                if not is_valid_email(watcher):
                    return f"Invalid watcher email: {watcher}", 400

            query = f"INSERT INTO {table_name} (name, exp_date, owner, watchers, comment) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (name, exp_date, owner, ", ".join(watcher_list), comment))

        connection.commit()

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    connection.close()
    return render_template('manage.html', tables=[t[0] for t in tables])

@app.route('/modify', methods=['GET', 'POST'])
def modify():
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

        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        columns = [col[0] for col in cursor.fetchall()]

        updates = []
        params = []

        for column in columns:
            if column not in ('id', 'insert_date', 'dom', 'name'):
                new_value = request.form.get(f'new_{column}')
                if new_value:
                    updates.append(f"{column} = %s")
                    params.append(new_value)

        if updates:
            updates.append("dom = CURRENT_TIMESTAMP")
            query = f"UPDATE {table_name} SET {', '.join(updates)} WHERE name = %s"
            params.append(row_name)
            cursor.execute(query, tuple(params))
            connection.commit()

    connection.close()
    return render_template('modify.html', success=True)

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')