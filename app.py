from flask import Flask, render_template, session, request, url_for, redirect
import psycopg
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
import os

app = Flask(__name__)
app.secret_key = 'supersecret'

load_dotenv()

DATABASE_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

def query_all(query, args=()):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, args)
            results = cur.fetchall()
    return results

def query_one(query, args=()):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, args)
            results = cur.fetchone()
    return results

def insert(query, args=()):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, args)
            conn.commit()

def isLoggedIn():
    if 'username' in session:
        return True
    return False

def get_db_connection():
    conn = psycopg.connect(**DATABASE_CONFIG)
    return conn

def register_viewer(username, password):
        try:
            hash = generate_password_hash(password)
            insert("INSERT INTO app_user (username, password_hash, role) VALUES (%s, %s, %s)", (username, hash, "viewer"))
            return True
        except Exception as e:
            print(f"Error registering user: {e}")
            return False

def login_user(username, password):
    try: 
        result = query_one("SELECT password_hash FROM app_user WHERE username = %s", (username,))
        if result and check_password_hash(result[0], password):
            return True

    except Exception as e:
        print(f"Error logging in user: {e}")
    return False

def get_employees():
    try:
        result = query_all("""
        SELECT e.fname || ' ' || e.minit || '. ' || e.lname AS full_name,
        d.dname AS department_name,
        COALESCE(dep.num_dependents, 0) AS num_dependents,
        COALESCE(w.num_projects, 0) as num_projects,
        COALESCE(w.total_hours, 0) AS total_hours

        FROM Employee e
        JOIN Department d ON e.dno = d.dnumber

        LEFT JOIN (
            SELECT Essn, COUNT(*) AS num_dependents
            FROM Dependent
            GROUP BY Essn
        ) dep ON e.ssn = dep.Essn

        LEFT JOIN (
            SELECT Essn, COUNT(DISTINCT Pno) AS num_projects, SUM(Hours)::int AS total_hours
            FROM Works_On
            GROUP BY Essn
        ) w ON e.ssn = w.Essn

        ORDER BY full_name;
        """)

        return result
    except Exception as e:
        print(f"Error fetching employees: {e}")
    return None
        
def get_portfolio():
    try:
        result = query_all("""
        SELECT p.pname AS project_name,
        pNumber AS project_number,
        d.dname AS department_name,
        COALESCE (COUNT(DISTINCT w.Essn), 0) AS headcount,
        COALESCE (SUM(w.Hours), 0)::int AS total_hours

        FROM Project p
        JOIN Department d ON p.dnum = d.dnumber

        LEFT JOIN Works_On w ON p.pnumber = w.Pno
        GROUP BY p.pname, d.dname, p.pnumber
        ORDER BY p.pname;
        """)

        return result
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
    return None

@app.route('/')
def index():
    if isLoggedIn():
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password','')
        if login_user(username, password):
            session['username'] = username
            session['role'] = 'viewer' #todo: fetch role from db

            return redirect(url_for('index'))
        else:
            error = 'Invalid credentials'

    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username','')
        password = request.form.get('password','')
        if register_viewer(username, password):
            return redirect(url_for('login'))
        else:
            error = 'Registration failed'
    
    return render_template('register.html', error=error)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/employees', methods=['GET', 'POST'])
def employees():
    if not isLoggedIn():
        return redirect(url_for('login'))
    employees = get_employees()
    if request.method == 'POST':
        # initially comes in as a string 
        sort_option = request.form.get('sortOption', '')
        if sort_option:
            sort_option = int(sort_option)
            if sort_option == 1:
                employees = sorted(employees, key=lambda x: x[0])
                # Sort by name ascending
            elif sort_option == 2:
                employees = sorted(employees, key=lambda x: x[0], reverse=True)
                # Sort by name descending
            elif sort_option == 3:
                employees = sorted(employees, key=lambda x: x[4])
                # Sort by hours ascending
            elif sort_option == 4:
                employees = sorted(employees, key=lambda x: x[4], reverse=True)
                # Sort by hours descending            
        
        dept_filter = request.form.get('departmentFilter', '')
        if dept_filter:
            employees = [emp for emp in employees if emp[1] == dept_filter]

        search_query = request.form.get('searchQuery', '')
        if search_query:
            employees = [emp for emp in employees if search_query.lower() in emp[0].lower()]


    return render_template('employees.html', employees=employees)

@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    if not isLoggedIn():
        return redirect(url_for('login'))
    
    projects = get_portfolio()
    if request.method == 'POST':
        # initially comes in as a string 
        sort_option = request.form.get('sortOption', '')
        if sort_option:
            sort_option = int(sort_option)
            if sort_option == 1:
                projects = sorted(projects, key=lambda x: x[2])
                # Sort by headcount ascending
            elif sort_option == 2:
                projects = sorted(projects, key=lambda x: x[2], reverse=True)
                # Sort by headcount descending
            elif sort_option == 3:
                projects = sorted(projects, key=lambda x: x[3])
                # Sort by hours ascending
            elif sort_option == 4:
                projects = sorted(projects, key=lambda x: x[3], reverse=True)
                # Sort by hours descending            

    return render_template('portfolio.html', projects=projects)


if __name__ == "__main__":
    app.run(debug=True)