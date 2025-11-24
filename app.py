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

def make_full_name(fname, minit, lname):
    # string concat in sql is so much simpler
    if minit:
        return f"{fname} {minit}. {lname}"
    return f"{fname} {lname}"

def get_employees():
    try:
        result = query_all("""
        SELECT e.fname, e.minit, e.lname,
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

        ORDER BY e.lname, e.fname, e.minit;
        """)

        employees = []
        for fname, minit, lname, dept_name, num_dependents, num_projects, total_hours in result:
            full_name = make_full_name(fname, minit, lname)

            employees.append((full_name, dept_name, num_dependents, num_projects, total_hours))

        return employees
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

def get_employees_on_project(project_number):
    # all employees on the project, for the table
    data = query_all("""
        SELECT
            e.fname, e.minit, e.lname,
            w.hours
        FROM Works_On w
        JOIN Employee e ON w.Essn = e.ssn
        WHERE w.Pno = %s
        ORDER BY e.lname, e.fname, e.minit;
    """, (project_number,))

    formatted_data = []
    for fname, minit, lname, hours in data:
        full_name = make_full_name(fname, minit, lname)

        formatted_data.append((full_name, hours))
    return formatted_data

def get_all_employees():
    # literally all employees, for the dropdown
    employees = query_all("""
        SELECT ssn,
        e.fname, e.minit, e.lname
        FROM Employee e
        ORDER BY e.lname, e.fname, e.minit;
    """)

    formatted_employees = []
    for ssn, fname, minit, lname in employees:
        full_name = make_full_name(fname, minit, lname)

        formatted_employees.append((ssn, full_name))
    return formatted_employees

def get_managers_overview():
    try:
        rows = query_all("""
            SELECT
                d.dname,
                d.dnumber,
                m.fname   AS mgr_fname,
                m.minit   AS mgr_minit,
                m.lname   AS mgr_lname,
                COALESCE(COUNT(DISTINCT e.ssn), 0) AS employee_count,
                COALESCE(SUM(w.hours), 0)::int     AS total_hours
            FROM Department d
            LEFT JOIN Employee m
                ON d.mgr_ssn = m.ssn
            LEFT JOIN Employee e
                ON e.dno = d.dnumber
            LEFT JOIN Works_On w
                ON w.essn = e.ssn
            GROUP BY
                d.dname, d.dnumber,
                m.fname, m.minit, m.lname
            ORDER BY d.dnumber;
        """)

        overview = []
        for dname, dnumber, mfname, mminit, mlname, emp_count, total_hours in rows:
            if mfname is None:
                manager_name = "N/A"
            else:
                manager_name = make_full_name(mfname, mminit, mlname)

            overview.append((dname, dnumber, manager_name, emp_count, total_hours))

        return overview
    except Exception as e:
        print(f"Error fetching managers overview: {e}")
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

@app.route('/projects/<int:project_number>')
def project_detail(project_number):
    if not isLoggedIn():
        return redirect(url_for('login'))

    project_data = get_employees_on_project(project_number)

    all_employees = get_all_employees()

    return render_template('project.html', data=project_data, employees=all_employees, project_number=project_number)

@app.route('/projects/add_employee_to_project', methods=['POST'])
def add_employee_to_project():
    if not isLoggedIn():
        return redirect(url_for('login'))

    project_number = int(request.form['project_number'])
    employee_ssn = request.form['employee_ssn']
    hours = float(request.form['hours'])

    insert("""
        INSERT INTO Works_On (Essn, Pno, Hours)
        VALUES (%s, %s, %s)
        ON CONFLICT (Essn, Pno)
        DO UPDATE SET Hours = Works_On.Hours + EXCLUDED.Hours;
    """, (employee_ssn, project_number, hours))

    return redirect(url_for('project_detail', project_number=project_number))

@app.route('/managers')
def managers_overview():
    if not isLoggedIn():
        return redirect(url_for('login'))

    managers = get_managers_overview()
    return render_template('managers.html', managers=managers) 

@app.route('/employees/add', methods=['GET', 'POST'])
def add_employee():
    if not isLoggedIn():
        return redirect(url_for('login'))

    if request.method == 'POST':
        ssn = request.form['ssn']
        fname = request.form['fname']
        minit = request.form.get('minit')
        lname = request.form['lname']
        address = request.form['address']
        sex = request.form['sex']
        salary = request.form['salary']
        dno = request.form['dno']

        try:
            query_one("""
                INSERT INTO employee (ssn, fname, minit, lname, address, sex, salary, dno)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (ssn, fname, minit, lname, address, sex, salary, dno))

            return redirect(url_for('employees'))

        except psycopg.errors.UniqueViolation:
            return render_template('add_employee.html', error="SSN already exists.")

        except psycopg.Error as e:
            return render_template('add_employee.html', error=str(e))

    return render_template('add_employee.html')

@app.route('/employees/edit/<ssn>', methods=['GET', 'POST'])
def edit_employee(ssn):
    if not isLoggedIn():
        return redirect(url_for('login'))

    if request.method == 'POST':
        address = request.form['address']
        salary = request.form['salary']
        dno = request.form['dno']

        try:
            insert("""
                UPDATE employee
                SET address = %s, salary = %s, dno = %s
                WHERE ssn = %s
            """, (address, salary, dno, ssn))

            return render_template('edit_employee.html', ssn=ssn, address=address, salary=salary, dno=dno)

        except psycopg.Error as e:
            return render_template('edit_employee.html', ssn=ssn, address=address, salary=salary, dno=dno)

    employee = query_one("""
        SELECT address, salary, dno
        FROM employee
        WHERE ssn = %s
    """, (ssn,))

    if employee:
        address, salary, dno = employee
        return render_template('edit_employee.html', ssn=ssn, address=address, salary=salary, dno=dno)
    else:
        return redirect(url_for('employees'))


@app.route('/employees/delete/<ssn>', methods=['POST', 'GET'])
def delete_employee(ssn):
    if not isLoggedIn():
        return redirect(url_for('login'))

    if request.method == 'GET':
        employee = query_one("""
            SELECT e.fname, e.minit, e.lname
            FROM employee e
            WHERE e.ssn = %s
        """, (ssn,))
        full_name = make_full_name(employee[0], employee[1], employee[2])

        return render_template('delete_employee.html', ssn=ssn, employee=full_name)
    
    try:
        employee = query_one("""
            SELECT e.fname, e.minit, e.lname
            FROM employee e
            WHERE e.ssn = %s
        """, (ssn,))
        full_name = make_full_name(employee[0], employee[1], employee[2])
        
        insert("""
            DELETE FROM employee
            WHERE ssn = %s
        """, (ssn,))

        return redirect(url_for('employees'))

    except psycopg.errors.ForeignKeyViolation:
        error = "Cannot delete employee: They are still assigned to projects, have dependents listed, or are a manager/supervisor."

        return render_template('delete_employee.html', employee=full_name, ssn=ssn, error=error)
    except psycopg.Error as e:
        return render_template('delete_employee.html', employee=full_name, ssn=ssn, error=e)


if __name__ == "__main__":
    app.run(debug=True)