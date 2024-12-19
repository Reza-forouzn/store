Here’s a simple `README.md` file for your project:

```markdown
# Database Management System with LDAP Authentication

This project is a web-based database management system that integrates with an LDAP server for user authentication. The system allows authenticated users to manage database tables and rows, with access control based on user roles (admin or owner).

## Features

- **LDAP Authentication**: Authenticate users against an LDAP server to fetch user details like email and validate credentials.
- **Role-Based Access Control**:
  - **Admins**: Full access to manage tables, rows, and modifications.
  - **Owners**: Limited access to manage rows they own.
- **Email Notifications**:
  - Notify admins, owners (old and new), and watchers (old and new) about changes to the database.
- **Audit Columns**:
  - Automatic population of `insert_date` and `dom` (date of modification) for changes.
- **Dynamic Table Management**:
  - Create tables dynamically.
  - Insert, modify, and track rows with column-level updates.

## Requirements

- Python 3.9+
- MySQL database
- OpenLDAP server

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/database-management-system.git
cd database-management-system
```

### 2. Install Dependencies
Create a virtual environment and install the required Python packages:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables
Set the following environment variables in your `docker-compose.yml` or `.env` file:
- `SECRET_KEY`: A secret key for Flask session management.
- `LDAP_SERVER`: The LDAP server URL (e.g., `ldap://your-ldap-server`).
- `LDAP_BASE_DN`: The base DN for LDAP queries.
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME`: MySQL database credentials.
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_EMAIL`, `SMTP_PASSWORD`: Email server settings.
- `ADMIN_EMAILS`: Comma-separated list of admin email addresses.

### 4. Run the Application
Run the application using Flask:
```bash
flask run --host=0.0.0.0 --port=5000
```

Alternatively, use Docker Compose:
```bash
docker-compose up --build
```

### 5. Access the Web Interface
Visit [http://localhost:5000](http://localhost:5000) in your browser.

## File Structure

- `app.py`: Main application logic.
- `templates/`: HTML templates for the frontend.
- `static/`: Static files (CSS, JS, etc.).
- `README.md`: Project documentation.

## Usage

- **Login**: Authenticate using your LDAP credentials.
- **Manage Tables**:
  - Create new tables (admins only).
  - Add new rows with automated email notifications.
- **Modify Data**:
  - Modify existing rows with audit tracking and role-based access control.
- **Admin Panel**:
  - View all tables and data (admins only).

## Contributing

Contributions are welcome! Please fork the repository and create a pull request.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

---

Happy coding!
```
