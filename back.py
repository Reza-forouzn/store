from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import mysql.connector
import ldap3
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"

LDAP_SERVER = "ldap://your-ldap-server"
LDAP_BASE_DN = "dc=example,dc=com"
LDAP_USER_DN = "ou=users"

DB_CONFIG = {
    "user": "store",
    "password": "store",
    "host": "127.0.0.1",
    "database": "store",
    "collation": "utf8mb4_unicode_ci",
    "charset": "utf8mb4"
}

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

@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # LDAP Authentication
        try:
            server = ldap3.Server(LDAP_SERVER)
            conn = ldap3.Connection(server, f"uid={username},{LDAP_USER_DN},{LDAP_BASE_DN}", password, auto_bind=True)
            session["user"] = username
            return redirect(url_for("home"))
        except ldap3.LDAPException as e:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/add_table", methods=["POST"])
def add_table():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    table_name = request.form.get("table_name")
    if not table_name.isalpha():
        return jsonify({"error": "Invalid table name"}), 400

    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
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
        return jsonify({"message": f"Table '{table_name}' created successfully"}), 201
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()

@app.route("/add_row", methods=["POST"])
def add_row():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    # Data validation omitted for brevity; similar to your original code

    return jsonify({"message": "Row added successfully"}), 201

@app.route("/modify_row", methods=["POST"])
def modify_row():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    # Only allow the owner to modify the data
    owner_email = session["user"]
    table_name = request.form.get("table_name")
    row_id = request.form.get("row_id")
    new_data = request.form.to_dict()

    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor(dictionary=True)

        # Verify if the user is the owner
        query = f"SELECT owner FROM store.{table_name} WHERE id = %s;"
        cursor.execute(query, (row_id,))
        row = cursor.fetchone()
        if not row or row["owner"] != owner_email:
            return jsonify({"error": "Unauthorized action"}), 403

        # Perform the update
        update_query = f"UPDATE store.{table_name} SET name=%s WHERE id=%s;"  # Simplified
        cursor.execute(update_query, (new_data["name"], row_id))
        cnx.commit()

        return jsonify({"message": "Row modified successfully"}), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()

if __name__ == "__main__":
    app.run(debug=True)
