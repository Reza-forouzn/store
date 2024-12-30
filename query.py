import mysql.connector
from datetime import datetime
import smtplib
import ssl
import re

def send_email(subject, body, receiver_email):
    """Send an email using the SMTP protocol."""
    port = 587
    smtp_server = "mail.mail"
    sender_email = "address@address"
    password = "pass"

    message = f"Subject: {subject}\n\n{body}"
    context = ssl.create_default_context()

    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)

def is_valid_email(email):
    """Validate email address using regex."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

try:
    # Connect to the database
    cnx = mysql.connector.connect(
        user="store",
        password="store",
        host="127.0.0.1",
        database="store",
        collation="utf8mb4_unicode_ci",
        charset="utf8mb4",
    )
    print("Connected to the database")
    cursor = cnx.cursor()

    # Query to find all tables in the 'store' database
    query_tables = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'store';"
    cursor.execute(query_tables)
    tables = [row[0] for row in cursor.fetchall()]  # Extract all table names

    current_date = datetime.today()

    for table_name in tables:
        # Get column names for each table
        columns_query = f"SELECT column_name FROM information_schema.columns WHERE table_schema = 'store' AND table_name = '{table_name}';"
        cursor.execute(columns_query)
        columns = [column[0] for column in cursor.fetchall()]

        # Check if required columns exist
        if 'name' in columns and 'exp_date' in columns and 'owner' in columns and 'watchers' in columns:
            # Fetch name, exp_date, owner, and watchers values
            select_query = f"SELECT name, exp_date, owner, watchers FROM {table_name};"
            cursor.execute(select_query)
            rows = cursor.fetchall()

            for row in rows:
                name, exp_date_value, owner, watchers = row

                # Convert exp_date to a datetime object
                try:
                    exp_date_obj = datetime.strptime(str(exp_date_value), '%Y-%m-%d')
                except ValueError:
                    print(f"Invalid date format for entry '{name}' in table '{table_name}'. Skipping.")
                    continue

                # Calculate the number of days until expiration
                remaining_days = (exp_date_obj - current_date).days

                # Create receiver_email list from owner and watchers
                receiver_email = []
                if is_valid_email(owner):
                    receiver_email.append(owner)
                if watchers:
                    watcher_list = [email.strip() for email in watchers.split(",") if is_valid_email(email.strip())]
                    receiver_email.extend(watcher_list)

                # Ensure no duplicate emails
                receiver_email = list(set(receiver_email))

                # Determine email subject and body based on remaining days
                # if remaining_days < 30:
                #     subject = f"Expiration Notification for {name}"
                #     body = f"The item '{name}' in table '{table_name}' has an expiration date of {exp_date_value} ({remaining_days} days remaining)."
                if 30 >= remaining_days > 15:
                    subject = f"Upcoming Expiration Alert for {name}"
                    body = f"The item '{name}' in table '{table_name}' is set to expire on {exp_date_value} ({remaining_days} days remaining)."
                elif 15 >= remaining_days > 10:
                    subject = f"Important Expiration Warning for {name}"
                    body = f"The item '{name}' in table '{table_name}' will expire soon on {exp_date_value} ({remaining_days} days remaining)."
                elif remaining_days <= 10:
                    subject = f"Critical Expiration Alert for {name}"
                    body = f"The item '{name}' in table '{table_name}' is critically close to expiration on {exp_date_value} ({remaining_days} days remaining)."
                else:
                    continue  # Skip sending email if no specific condition matches

                # Send email
                if receiver_email:
                    send_email(subject, body, receiver_email)

except mysql.connector.Error as err:
    print(f"Database Error: {err}")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'cnx' in locals() and cnx.is_connected():
        cnx.close()
        print("Database connection closed.")
