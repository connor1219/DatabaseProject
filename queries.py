# authentication queries
GET_USER_AUTH = "SELECT password_hash, role FROM app_user WHERE username = %s"
GET_ALL_USERS = "SELECT id, username, role FROM app_user ORDER BY id"
INSERT_USER = "INSERT INTO app_user (username, password_hash, role) VALUES (%s, %s, %s)"

# department queries
GET_DEPARTMENTS = "SELECT dnumber, dname FROM Department ORDER BY dname"
GET_DEPARTMENTS_LOWER = "SELECT Dnumber, Dname FROM department ORDER BY Dname"

# employee queries
GET_EMPLOYEES_WITH_STATS = """
    SELECT e.ssn, e.fname, e.minit, e.lname, d.dname AS department_name,
           COALESCE(dep.num_dependents, 0) AS num_dependents,
           COALESCE(w.num_projects, 0) as num_projects,
           COALESCE(w.total_hours, 0) AS total_hours
    FROM Employee e
    JOIN Department d ON e.dno = d.dnumber
    LEFT JOIN (SELECT Essn, COUNT(*) AS num_dependents FROM Dependent GROUP BY Essn) dep ON e.ssn = dep.Essn
    LEFT JOIN (SELECT Essn, COUNT(DISTINCT Pno) AS num_projects, SUM(Hours)::int AS total_hours FROM Works_On GROUP BY Essn) w ON e.ssn = w.Essn
    WHERE 1=1
"""

GET_EMPLOYEES_LIST = """
    SELECT e.Ssn, e.Fname, e.Minit, e.Lname, e.Address, e.Salary,
           COALESCE(d.Dname, 'No Department') AS department_name
    FROM employee e
    LEFT JOIN department d ON e.Dno = d.Dnumber
    ORDER BY e.Lname, e.Fname
"""

GET_ALL_EMPLOYEES_NAMES = "SELECT Ssn, Fname, Minit, Lname FROM Employee ORDER BY Lname, Fname"

GET_EMPLOYEE_BY_SSN = "SELECT ssn, fname, minit, lname, bdate, address, sex, salary, dno FROM employee WHERE ssn = %s"

GET_EMPLOYEE_NAME_BY_SSN = "SELECT e.fname, e.minit, e.lname FROM employee e WHERE e.ssn = %s"

GET_SUPERVISORS = "SELECT Ssn, Fname, Minit, Lname FROM employee ORDER BY Fname, Lname"

INSERT_EMPLOYEE = "INSERT INTO employee (ssn, fname, minit, lname, bdate, address, sex, salary, super_ssn, dno) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

INSERT_EMPLOYEE_IMPORT = "INSERT INTO employee (ssn, fname, minit, lname, bdate, address, sex, salary, dno) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"

UPDATE_EMPLOYEE = "UPDATE employee SET address = %s, salary = %s, dno = %s WHERE ssn = %s"

DELETE_EMPLOYEE = "DELETE FROM employee WHERE ssn = %s"

# project queries
def get_projects_query(sort_column, sort_direction):
    """Returns projects query with specified sorting"""
    return f"""
        SELECT p.Pnumber, p.Pname AS project_name,
               COALESCE(d.Dname, 'No Department') AS department_name,
               COUNT(DISTINCT w.Essn) AS headcount,
               COALESCE(SUM(w.Hours), 0) AS total_hours
        FROM project p
        LEFT JOIN department d ON p.Dnum = d.Dnumber
        LEFT JOIN works_on w ON p.Pnumber = w.Pno
        GROUP BY p.Pnumber, p.Pname, d.Dname
        ORDER BY {sort_column} {sort_direction}
    """

GET_PROJECT_BY_ID = """
    SELECT p.Pnumber, p.Pname, p.Plocation, d.Dname
    FROM Project p
    LEFT JOIN Department d ON p.Dnum = d.Dnumber
    WHERE p.Pnumber = %s
"""

GET_PROJECT_EMPLOYEES = """
    SELECT e.Ssn, e.Fname, e.Minit, e.Lname, w.Hours
    FROM Works_On w
    JOIN Employee e ON w.Essn = e.Ssn
    WHERE w.Pno = %s
    ORDER BY e.Lname, e.Fname
"""

INSERT_WORKS_ON = """
    INSERT INTO Works_On (Essn, Pno, Hours) VALUES (%s, %s, %s)
    ON CONFLICT (Essn, Pno) DO UPDATE SET Hours = Works_On.Hours + EXCLUDED.Hours
"""

# manager queries
GET_MANAGERS_WITH_STATS = """
    SELECT d.Dnumber, d.Dname, m.Fname, m.Minit, m.Lname,
           COUNT(DISTINCT e.Ssn) AS headcount,
           COALESCE(SUM(w.Hours), 0) AS total_hours
    FROM department d
    LEFT JOIN employee m ON d.Mgr_ssn = m.Ssn
    LEFT JOIN employee e ON d.Dnumber = e.Dno
    LEFT JOIN works_on w ON e.Ssn = w.Essn
    GROUP BY d.Dnumber, d.Dname, m.Fname, m.Minit, m.Lname
    ORDER BY d.Dnumber ASC
"""
