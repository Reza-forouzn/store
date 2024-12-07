from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

app = Flask(__name__)

# MySQL configuration
DB_CONFIG = {
    'user': 'store',
    'password': 'store',
    'host': '127.0.0.1',
    'database': 'store',
    'collation': 'utf8mb4_unicode_ci',
    'charset': 'utf8mb4',
}

# Email Configuration
SMTP_SERVER = 'mail.mail'
SMTP_PORT = 587
SENDER_EMAIL = 'address@address'
SENDER_PASSWORD = 'pass'

# Helper functions
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
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Routes
@app.route('/create_table', methods=['POST'])
def create_table():
    try:
        table_name = request.json.get('table_name').strip().lower()
        if not table_name.isalpha():
            return jsonify({"error": "Invalid table name"}), 400
        
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Check if table already exists
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'store';"
        cursor.execute(query)
        if table_name in [row[0] for row in cursor.fetchall()]:
            return jsonify({"error": f"Table {table_name} already exists"}), 400

        # Create table
        cursor.execute(f"""
        CREATE TABLE store.{table_name} (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            insert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dom TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            exp_date DATE NOT NULL,
            owner VARCHAR(255) NOT NULL,
            watchers VARCHAR(1000),
            comment VARCHAR(1000)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        connection.commit()
        return jsonify({"message": f"Table {table_name} created successfully"}), 201
    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/add_row', methods=['POST'])
def add_row():
    try:
        data = request.json
        table_name = data['table_name']
        name = data['name']
        exp_date = data['exp_date']
        owner = data['owner']
        watchers = data.get('watchers', [])
        comment = data.get('comment', '')

        if not is_valid_date(exp_date):
            return jsonify({"error": "Invalid date format"}), 400
        if not is_valid_email(owner):
            return jsonify({"error": "Invalid owner email"}), 400
        for watcher in watchers:
            if not is_valid_email(watcher):
                return jsonify({"error": f"Invalid watcher email: {watcher}"}), 400

        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        cursor.execute(f"""
        INSERT INTO store.{table_name} (name, exp_date, owner, watchers, comment)
        VALUES (%s, %s, %s, %s, %s);
        """, (name, exp_date, owner, ", ".join(watchers), comment))
        connection.commit()
        return jsonify({"message": "Row added successfully"}), 201
    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/notify', methods=['GET'])
def notify():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'store';"
        cursor.execute(query)
        tables = [row[0] for row in cursor.fetchall()]
        current_date = datetime.today()

        notifications = []

        for table in tables:
            cursor.execute(f"SELECT name, exp_date, owner, watchers FROM {table}")
            rows = cursor.fetchall()
            for row in rows:
                name, exp_date, owner, watchers = row
                remaining_days = (exp_date - current_date).days
                emails = [owner] + (watchers.split(", ") if watchers else [])
                emails = [email for email in emails if is_valid_email(email)]

                if remaining_days <= 10:
                    subject = f"Critical Alert: {name} expiring soon!"
                    body = f"{name} is expiring on {exp_date} ({remaining_days} days left)."
                    for email in set(emails):
                        send_email(subject, body, email)
                        notifications.append({"name": name, "email": email})
        
        return jsonify(notifications), 200
    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
