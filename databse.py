import mysql.connector
import re
from datetime import datetime

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
        print("1. Add a new table")
        print("2. Add a new row to an existing table")
        print("3. Exit")
        choice = input("Please choose an option (1/2/3): ").strip()

        if choice == "1":
            # Add a new table
            table_name = input("Enter the new table name: ").strip().lower()
            if not table_name.isalpha():
                print("Invalid table name. Table names should contain only alphabetic characters.")
                continue

            # Check if table already exists
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'store';"
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            if table_name in tables:
                print(f"Table '{table_name}' already exists.")
                continue

            # Create the table
            query = f"""
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
            """
            cursor.execute(query)
            cnx.commit()
            print(f"Table '{table_name}' has been created successfully.")

        elif choice == "2":
            # Add a new row to an existing table
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'store';"
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            if not tables:
                print("No tables exist. Please create a table first.")
                continue

            print("Existing tables:")
            for table in tables:
                print(f"- {table}")
            
            table_name = input("Enter the table name to insert into: ").strip().lower()
            if table_name not in tables:
                print(f"Table '{table_name}' does not exist.")
                continue

            # Input row details
            name = input("Enter name: ").strip()
            exp_date = input("Enter expiration date (YYYY-MM-DD): ").strip()
            if not is_valid_date(exp_date):
                print("Invalid date format. Please use YYYY-MM-DD.")
                continue

            owner = input("Enter owner email: ").strip()
            if not is_valid_email(owner):
                print("Invalid email format.")
                continue

            watchers = input("Enter watcher(s) email(s) (comma-separated): ").strip()
            watcher_list = [email.strip() for email in watchers.split(",")]
            for watcher in watcher_list:
                if not is_valid_email(watcher):
                    print(f"Invalid watcher email: {watcher}")
                    continue

            comment = input("Enter a comment: ").strip()

            # Insert into the table
            insert_query = f"""
            INSERT INTO store.{table_name} (name, exp_date, owner, watchers, comment)
            VALUES (%s, %s, %s, %s, %s);
            """
            cursor.execute(insert_query, (name, exp_date, owner, ", ".join(watcher_list), comment))
            cnx.commit()
            print(f"Row has been added to '{table_name}'.")

        elif choice == "3":
            # Exit the program
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
