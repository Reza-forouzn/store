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

    # Check existing tables
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'store';"
    cursor.execute(query)
    tables = [row[0] for row in cursor.fetchall()]  # Extract table names

    # Display current tables if they exist
    if tables:
        print("Current tables in the 'store' database:")
        for table in tables:
            print(f"- {table}")
    else:
        print("No tables currently exist in the 'store' database.")

    # Input and validate table name
    retry_counter = 0
    max_retries = 10
    while retry_counter < max_retries:
        x = input("Please insert the table name: ").strip().replace(" ", "")
        while not x.isalpha():
            retry_counter += 1
            if retry_counter >= max_retries:
                print("Maximum retry attempts reached. Exiting.")
                raise Exception("Too many retries.")
            x = input("Invalid input. Please insert a valid table name: ").strip().replace(" ", "")
        x = x.lower()

        # Check if the table name exists
        if x in tables:
            print(f"Table '{x}' already exists in the database. Please choose a different name.")
            retry_counter += 1
            if retry_counter >= max_retries:
                print("Maximum retry attempts reached. Exiting.")
                raise Exception("Too many retries.")
        else:
            break  # Exit the loop if the table name is valid and does not exist

    if retry_counter < max_retries:
        # Create the table
        query = f"""
        CREATE TABLE store.{x} (
            id INT PRIMARY KEY AUTO_INCREMENT,            -- Unique identifier for each row
            name VARCHAR(255) NOT NULL,                   -- Name column
            insert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Automatically set to the current date/time on insert
            exp_date DATE NOT NULL,                       -- Expected date column
            owner VARCHAR(255) NOT NULL,                  -- Owner email address
            watchers VARCHAR(1000),                       -- Comma-separated list of email addresses
            commen VARCHAR(1000)                          -- Comment column
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        cursor.execute(query)
        cnx.commit()
        print(f"New table '{x}' has been created in the database.")

    # Optionally, insert data into the table
    if retry_counter < max_retries:
        while retry_counter < max_retries:
            name = input("Please input name as identifier: ").strip()
            query = f"SELECT COUNT(*) FROM store.{x} WHERE name = %s;"
            cursor.execute(query, (name,))
            if cursor.fetchone()[0] > 0:
                print(f"The name '{name}' already exists in the table '{x}'. Please choose a different name.")
                retry_counter += 1
                if retry_counter >= max_retries:
                    print("Maximum retry attempts reached. Exiting.")
                    raise Exception("Too many retries.")
                continue

            # Input and validate date of expiration
            while True:
                doe = input("Please input date of expiration (YYYY-MM-DD): ").strip()
                if is_valid_date(doe):
                    break
                print("Invalid date format. Please use YYYY-MM-DD.")

            # Input and validate owner email
            owner = input("Please input owner email address: ").strip()
            while not is_valid_email(owner):
                retry_counter += 1
                if retry_counter >= max_retries:
                    print("Maximum retry attempts reached. Exiting.")
                    raise Exception("Too many retries.")
                owner = input("Invalid email format. Please input a valid owner email address: ").strip()

            # Input and validate watcher(s) email(s)
            watchers = input("Please input watcher(s) email(s) (comma-separated): ").strip()
            watcher_list = [email.strip() for email in watchers.split(",")]
            for i, watcher in enumerate(watcher_list):
                while not is_valid_email(watcher):
                    retry_counter += 1
                    if retry_counter >= max_retries:
                        print("Maximum retry attempts reached. Exiting.")
                        raise Exception("Too many retries.")
                    watcher_list[i] = input(f"Invalid email format for '{watcher}'. Please input a valid email address: ").strip()

            watchers = ", ".join(watcher_list)
            comment = input("Please input a comment: ").strip()

            # Insert data into the table
            insert_query = f"""
            INSERT INTO store.{x} (name, exp_date, owner, watchers, commen)
            VALUES (%s, %s, %s, %s, %s);
            """
            cursor.execute(insert_query, (name, doe, owner, watchers, comment))
            cnx.commit()
            print("Record has been inserted into the table.")
            break  # Exit loop after successful insertion

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
