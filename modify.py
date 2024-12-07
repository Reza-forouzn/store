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

def edit_table_data(cnx, cursor, table_name, row_id):
    """Edit specific row data (except owner and watchers)."""
    print(f"Editing data for row with ID {row_id} in table {table_name}:")
    columns_query = f"SELECT column_name FROM information_schema.columns WHERE table_schema = 'store' AND table_name = '{table_name}';"
    cursor.execute(columns_query)
    columns = [col[0] for col in cursor.fetchall()]

    # Exclude "owner" and "watchers" columns
    editable_columns = [col for col in columns if col not in ('owner', 'watchers')]

    updates = {}
    for col in editable_columns:
        value = input(f"Enter new value for '{col}' (leave blank to skip): ").strip()
        if value:
            updates[col] = value

    if updates:
        set_clause = ", ".join([f"{col} = %s" for col in updates.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s;"
        cursor.execute(query, tuple(updates.values()) + (row_id,))
        cnx.commit()
        print("Row updated successfully.")
    else:
        print("No changes made.")

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
        if 'dom' in columns and 'insert_date' in columns and 'owner' in columns and 'watchers' in columns:
            # Fetch dom, insert_date, owner, and watchers values
            select_query = f"SELECT id, dom, insert_date, owner, watchers FROM {table_name};"
            cursor.execute(select_query)
            rows = cursor.fetchall()

            for row in rows:
                row_id, dom, insert_date, owner, watchers = row

                # Compare dom and insert_date
                if str(dom) != str(insert_date):
                    # Notify owner and watchers
                    receiver_email = []
                    if is_valid_email(owner):
                        receiver_email.append(owner)
                    if watchers:
                        watcher_list = [email.strip() for email in watchers.split(",") if is_valid_email(email.strip())]
                        receiver_email.extend(watcher_list)

                    # Ensure no duplicate emails
                    receiver_email = list(set(receiver_email))

                    # Prepare email content
                    subject = f"DOM Mismatch Alert for Table {table_name} - ID {row_id}"
                    body = (
                        f"Mismatch found in table '{table_name}' for ID {row_id}:\n"
                        f"DOM: {dom}\n"
                        f"Insert Date: {insert_date}\n\n"
                        f"Please review the data and take necessary action."
                    )

                    # Send email
                    if receiver_email:
                        send_email(subject, body, receiver_email)

                    # Prompt to edit data
                    edit_choice = input(f"Would you like to edit data for ID {row_id} in table '{table_name}'? (yes/no): ").strip().lower()
                    if edit_choice == 'yes':
                        edit_table_data(cnx, cursor, table_name, row_id)

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
