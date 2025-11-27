# CIS3530 A4

## Setup

### Windows

```bash
# 1. clone or download the project
https://github.com/connor1219/DatabaseProject
cd DatabaseProject

# 2. create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. install dependencies
pip install -r requirements.txt

# 4. set up PostgreSQL database
 psql -U postgres
 CREATE DATABASE test_company_db;

# 5. create config.py file
echo SECRET_KEY = 'supersecret' > config.py
echo DEBUG = False >> config.py
echo DB_NAME = 'my_company_db' >> config.py
echo DB_USER = 'postgres' >> config.py
echo DB_PASSWORD = '123' >> config.py
echo DB_HOST = 'localhost' >> config.py
echo DB_PORT = '5432' >> config.py

# 6. Initialize database schema
psql -U postgres -d test_company_db -f company_v3.02.sql

# 7. Create application tables and indexes
psql -U postgres -d test_company_db -f team_setup.sql

# 8. Run the application
flask run

```

### Linux

```bash

# 1. clone or download the project
git clone <repository-url>
cd DatabaseProject

# 2. create virtual environment
python -m venv .venv
source .venv\bin\activate

# 3. install dependencies
pip install -r requirements.txt

# 4. set up PostgreSQL database
 psql -U postgres
 CREATE DATABASE test_company_db;

# 5. create config.py file
echo SECRET_KEY = 'supersecret' > config.py
echo DEBUG = False >> config.py
echo DB_NAME = 'my_company_db' >> config.py
echo DB_USER = 'postgres' >> config.py
echo DB_PASSWORD = '123' >> config.py
echo DB_HOST = 'localhost' >> config.py
echo DB_PORT = '5432' >> config.py

# 6. Initialize database schema
psql -U postgres -d test_company_db -f company_v3.02.sql

# 7. Create application tables and indexes
psql -U postgres -d test_company_db -f team_setup.sql

# 8. Run the application
flask run

```

## Index Rational

```
CREATE INDEX idx_employee_name ON Employee (Lname, Fname, Minit);
```
We chose this index as a few queries sort or retrieve employees by last name and first name. By indexing (Lname, Fname, Minit), the database can return results in sorted order directly from the index instead of scanning and sorting the entire table.

```
CREATE INDEX idx_employee_dno ON Employee (Dno)
```
Since a few queries filter or join on Employee.Dno, an index allows the database to quickly locate all employees belonging to a specific department instead of scanning the entire table. This makes the corresponding JOINs, WHERE filters, and GROUP BY operations much faster. 
