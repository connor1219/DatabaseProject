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

```

## Index Rational

- TODO
