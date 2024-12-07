import mysql.connector
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def is_valid_email(email):
    """Validate email address using regex."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def is_valid_date(date_text):
    """Validate date in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def send_email(subject, body, receiver_email):
    """Send an email using the SMTP protocol."""
    port = 587
    smtp_server = "mail.mail"
    sender_email = "address@address"
    password = "pass"

    try:
        # Set up the email
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to SMTP server
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"Email sent to {receiver_email}")
    except Exception as e:
        print(f"Failed to send email to {receiver_email}: {e}")

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

    while True:
        # Display menu
        print("\nOptions:")
        print("1. Modify row data in a table")
        print("2. Exit")
        choice = input("Please choose an option (1/2): ").strip()

        if choice == "1":
            # Get the table name
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'store';"
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            if not tables:
                print("No tables exist. Please create a table first.")
                continue

            print("Existing tables:")
            for table in tables:
                print(f"- {table}")

            table_name = input("Enter the table name: ").strip().lower()
            if table_name not in tables:
                print(f"Table '{table_name}' does not exist.")
                continue

            # Get the row to modify
            name = input("Enter the name identifier of the row to modify: ").strip()
            query = f"SELECT id, owner, watchers, exp_date FROM store.{table_name} WHERE name = %s;"
            cursor.execute(query, (name,))
            row = cursor.fetchone()
            if not row:
                print(f"No row found with name '{name}'.")
                continue

            row_id, old_owner, old_watchers, old_exp_date = row
            print(f"\nCurrent values:\n- Owner: {old_owner}\n- Watchers: {old_watchers}\n- Expiration Date: {old_exp_date}")

            # Modify columns
            new_owner = input("Enter new owner email (leave blank to keep current): ").strip()
            new_watchers = input("Enter new watchers email(s) (comma-separated, leave blank to keep current): ").strip()
            new_exp_date = input("Enter new expiration date (YYYY-MM-DD, leave blank to keep current): ").strip()

            if new_owner and not is_valid_email(new_owner):
                print("Invalid email format for owner.")
                continue

            if new_watchers:
                watcher_list = [email.strip() for email in new_watchers.split(",")]
                for watcher in watcher_list:
                    if not is_valid_email(watcher):
                        print(f"Invalid watcher email: {watcher}")
                        continue
                new_watchers = ", ".join(watcher_list)
            else:
                new_watchers = old_watchers

            if new_exp_date and not is_valid_date(new_exp_date):
                print("Invalid date format. Please use YYYY-MM-DD.")
                continue

            # Determine changes
            changes = {}
            if new_owner and new_owner != old_owner:
                changes["owner"] = (old_owner, new_owner)
            if new_watchers and new_watchers != old_watchers:
                changes["watchers"] = (old_watchers, new_watchers)
            if new_exp_date and new_exp_date != old_exp_date:
                changes["exp_date"] = (old_exp_date, new_exp_date)

            if not changes:
                print("No changes were made.")
                continue

            # Update the database
            update_query = f"""
            UPDATE store.{table_name}
            SET owner = %s, watchers = %s, exp_date = %s, dom = CURRENT_TIMESTAMP
            WHERE id = %s;
            """
            cursor.execute(update_query, (new_owner or old_owner, new_watchers, new_exp_date or old_exp_date, row_id))
            cnx.commit()
            print("Row updated successfully.")

            # Notify old and new emails
            old_emails = [old_owner] + old_watchers.split(", ")
            new_emails = [new_owner or old_owner] + new_watchers.split(", ")
            subject = "Database Row Update Notification"
            body = f"The following changes were made:\n{changes}"

            for email in set(old_emails + new_emails):
                send_email(subject, body, email)

        elif choice == "2":
            print("Exiting program.")
            break

        else:
            print("Invalid choice. Please try again.")

except mysql.connector.Error as err:
    print(f"Error: {err}")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'cnx' in locals() and cnx.is_connected():
        cnx.close()
        print("Database connection closed.")
