from config import SECRET_KEY, DEBUG
from flask import Flask, render_template, session, request, url_for, redirect, flash, make_response
from helper import (validate_registration, make_full_name, query_one, query_all, insert,
                    get_db_connection, login_required, admin_required, validate_sort,
                    build_employee_list)
from werkzeug.security import check_password_hash, generate_password_hash
import queries as Q
import psycopg
import csv
import io
from openpyxl import load_workbook

app = Flask(__name__)
app.secret_key = SECRET_KEY

# -------------------------------------------------------------------------------- #
# ------------------------------------- AUTH ------------------------------------- #
# -------------------------------------------------------------------------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username, password = request.form.get('username', ''), request.form.get('password', '')
        try:
            result = query_one(Q.GET_USER_AUTH, (username,))
            if result and check_password_hash(result[0], password):
                session['username'], session['role'] = username, result[1]
                return redirect(url_for('employees'))
            error = 'Invalid credentials'

        except Exception:
            error = 'Invalid credentials'

    return render_template('auth/login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()

    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        username, password, role = request.form.get('username', ''), request.form.get('password', ''), request.form.get('role', '')
        is_valid, validation_error = validate_registration(username, password, role)
        if not is_valid:
            error = validation_error
        else:
            try:
                insert(Q.INSERT_USER, (username, generate_password_hash(password), role))
                return redirect(url_for('login'))
            except Exception:
                error = 'Registration failed. Please try again.'
    return render_template('auth/register.html', error=error)

# -------------------------------------------------------------------------------- #
# ----------------------------------- EMPLOYEES ---------------------------------- #
# -------------------------------------------------------------------------------- #

@app.route('/')
@login_required
def employees():
    dept_filter = request.args.get('department', '')
    name_filter = request.args.get('name', '').strip()
    sort_by, sort_order, sort_column, sort_direction = validate_sort(
        request.args.get('sort', 'name'), request.args.get('order', 'asc'),
        {'name': 'full_name', 'total_hours': 'total_hours'}
    )

    query = Q.GET_EMPLOYEES_WITH_STATS

    params = []

    if dept_filter:
        query += " AND d.Dnumber = %s"
        params.append(dept_filter)

    query += f" ORDER BY {'e.Lname ' + sort_direction + ', e.Fname ' + sort_direction if sort_column == 'full_name' else sort_column + ' ' + sort_direction}"

    try:
        raw_employees = query_all(query, params)
        employees = build_employee_list(raw_employees)

        if name_filter:
            employees = [emp for emp in employees if name_filter.lower() in emp[1].lower()]

        departments = query_all(Q.GET_DEPARTMENTS)

    except Exception:
        employees, departments = [], []

    return render_template('employees/index.html', employees=employees, departments=departments,
                         current_dept=dept_filter, current_name=name_filter,
                         current_sort=sort_by, current_order=sort_order)

@app.route('/employees')
@login_required
def employees_manager():
    raw_employees = query_all(Q.GET_EMPLOYEES_LIST)
    employees = build_employee_list(raw_employees)
    return render_template('employees/manager/index.html', employees=employees)

@app.route('/employees/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_employee():
    try:
        departments = query_all(Q.GET_DEPARTMENTS_LOWER)
        supervisors_raw = query_all(Q.GET_SUPERVISORS)
        supervisors = [(ssn, make_full_name(fname, minit, lname)) for ssn, fname, minit, lname in supervisors_raw]
    except Exception:
        departments, supervisors = [], []

    if request.method == 'POST':
        fields = ['ssn', 'fname', 'minit', 'lname', 'bdate', 'address', 'sex', 'salary', 'super_ssn', 'dno']
        values = tuple(request.form.get(f) or None for f in fields)

        try:
            insert(Q.INSERT_EMPLOYEE, values)
            flash('Employee added successfully', 'success')
            return redirect(url_for('employees_manager'))

        except psycopg.errors.UniqueViolation:
            return render_template('employees/manager/add.html',
                                 error="SSN already exists.",
                                 departments=departments,
                                 supervisors=supervisors,
                                 form_data=request.form)

        except psycopg.Error as e:
            return render_template('employees/manager/add.html',
                                 error=str(e),
                                 departments=departments,
                                 supervisors=supervisors,
                                 form_data=request.form)

    return render_template('employees/manager/add.html', departments=departments, supervisors=supervisors)

@app.route('/employees/edit/<ssn>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(ssn):
    if request.method == 'POST':
        try:
            insert(Q.UPDATE_EMPLOYEE, (request.form['address'], request.form['salary'], request.form.get('dno') or None, ssn))
            flash('Employee updated successfully', 'success')
            return redirect(url_for('employees_manager'))
        except psycopg.Error as e:
            flash(f'Error updating employee: {str(e)}', 'error')

    employee = query_one(Q.GET_EMPLOYEE_BY_SSN, (ssn,))
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('employees_manager'))

    departments = query_all(Q.GET_DEPARTMENTS)
    return render_template('employees/manager/edit.html', employee=employee, departments=departments)

@app.route('/employees/delete/<ssn>', methods=['POST', 'GET'])
@login_required
@admin_required
def delete_employee(ssn):
    employee = query_one(Q.GET_EMPLOYEE_NAME_BY_SSN, (ssn,))
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('employees_manager'))

    full_name = make_full_name(*employee)

    if request.method == 'GET':
        return render_template('employees/manager/delete.html', ssn=ssn, employee=full_name)

    try:
        insert(Q.DELETE_EMPLOYEE, (ssn,))
        flash(f'Employee {full_name} deleted successfully', 'success')
        return redirect(url_for('employees_manager'))
    except psycopg.errors.ForeignKeyViolation:
        flash('Cannot delete employee: They are still assigned to projects, have dependents listed, or are a manager/supervisor.', 'error')
        return redirect(url_for('employees_manager'))
    except psycopg.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('employees_manager'))

# -------------------------------------------------------------------------------- #
# ----------------------------------- PROJECTS ----------------------------------- #
# -------------------------------------------------------------------------------- #

@app.route('/projects')
@login_required
def projects():
    sort_by, sort_order, sort_column, sort_direction = validate_sort(
        request.args.get('sort', 'name'), request.args.get('order', 'asc'),
        {'name': 'p.Pname', 'headcount': 'headcount', 'total_hours': 'total_hours'}
    )
    projects = query_all(Q.get_projects_query(sort_column, sort_direction))
    export_url = url_for('export_projects_csv', sort=sort_by, order=sort_order)
    return render_template('projects/index.html', projects=projects,
                         current_sort=sort_by, current_order=sort_order, export_url=export_url)

@app.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@login_required
def project_details(project_id):
    if request.method == 'POST':
        try:
            insert(Q.INSERT_WORKS_ON, (request.form['employee_ssn'], project_id, float(request.form['hours'])))
            flash('Employee assigned successfully', 'success')
            return redirect(url_for('project_details', project_id=project_id))
        except Exception as e:
            flash(f'Error assigning employee: {str(e)}', 'error')

    project = query_one(Q.GET_PROJECT_BY_ID, (project_id,))
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects'))

    employees_data = query_all(Q.GET_PROJECT_EMPLOYEES, (project_id,))
    employees_on_project = [(ssn, make_full_name(fname, minit, lname), hours)
                           for ssn, fname, minit, lname, hours in employees_data]

    all_employees_data = query_all(Q.GET_ALL_EMPLOYEES_NAMES)
    all_employees = [(ssn, make_full_name(fname, minit, lname))
                    for ssn, fname, minit, lname in all_employees_data]

    return render_template('projects/detail.html', project=project,
                         employees_on_project=employees_on_project, all_employees=all_employees)


# -------------------------------------------------------------------------------- #
# -------------------------- CSV/EXCEL EXPORT/IMPORT  ---------------------------- #
# -------------------------------------------------------------------------------- #

@app.route('/projects/import/csv', methods=['POST'])
@login_required
def import_projects_csv():
    if 'xlsx_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('employees_manager'))
    
    file = request.files['xlsx_file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('employees_manager'))
    
    if not file.filename.endswith('.xlsx'):
        flash('File must be a .xlsx file', 'error')
        return redirect(url_for('employees_manager'))
    
    try:
        wb = load_workbook(file, read_only=True)
        ws = wb.active
        
        headers = [cell.value for cell in ws[1]]
        headers = [str(h).strip() if h else '' for h in headers]
        
        rows_data = []
        # Starts on row 2 to skip headers
        for row in ws.iter_rows(min_row=2, values_only=True):
            if any(cell is not None for cell in row):
                rows_data.append([cell for cell in row])
        
        if not rows_data:
            flash('No data rows found in file', 'error')
            return redirect(url_for('employees_manager'))
        
        expected_headers = ['Ssn', 'Fname', 'Minit', 'Lname', 'BDate', 'Address', 'Sex', 'Salary', 'Dno']
        if not all(h in headers for h in expected_headers):
            flash(f'Invalid format. Expected columns: {", ".join(expected_headers)}', 'error')
            return redirect(url_for('employees_manager'))
        
        header_indices = {h: headers.index(h) for h in expected_headers}
        
        success_count = 0
        error_messages = []
        
        for row_idx, row in enumerate(rows_data, start=2):
            try:
                values = tuple(
                    row[header_indices[h]] if header_indices[h] < len(row) else None 
                    for h in expected_headers
                )
                values = tuple(None if v == '' or v is None else v for v in values)
                
                # Salary is NOT NULL
                if not values[7]:  
                    error_messages.append(f'Row {row_idx}: Salary is required and cannot be empty')
                    continue

                # Dno is NOT NULL
                if not values[8]:  
                    error_messages.append(f'Row {row_idx}: Department number (Dno) is required and cannot be empty')
                    continue
                

                processed_values = []
                for i, v in enumerate(values):
                    # Salary required, must be valid integer
                    if i == 7:
                        try:
                            processed_values.append(int(float(v)))
                        except (ValueError, TypeError):
                            error_messages.append(f'Row {row_idx}: Salary must be a valid number, got "{v}"')
                            break
                     # Dno required, must be valid integer
                    elif i == 8:
                        try:
                            processed_values.append(int(float(v)))
                        except (ValueError, TypeError):
                            error_messages.append(f'Row {row_idx}: Department number (Dno) must be a valid number, got "{v}"')
                            break
                    else:
                        # Dates and other fields pass through as-is
                        processed_values.append(v)  
                
                # Only insert if we didn't hit validation errors
                if len(processed_values) == len(expected_headers):
                    insert(Q.INSERT_EMPLOYEE_IMPORT, tuple(processed_values))
                    success_count += 1
            except psycopg.errors.UniqueViolation:
                error_messages.append(f'Row {row_idx}: SSN already exists')
            except psycopg.Error as e:
                error_messages.append(f'Row {row_idx}: {str(e)}')
        
        # Prepare success/error messages
        if success_count > 0:
            success_msg = f'Successfully imported {success_count} employee(s)'
            if error_messages:
                success_msg += f'. {len(error_messages)} row(s) failed'
                flash(success_msg, 'warning')
                for err in error_messages[:10]:
                    flash(err, 'error')
            else:
                flash(success_msg, 'success')
        else:
            if error_messages:
                flash('No employees imported. Errors occurred:', 'error')
                for err in error_messages[:10]:
                    flash(err, 'error')
            else:
                flash('No employees imported', 'error')
        
        return redirect(url_for('employees_manager'))
    
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('employees_manager'))
    

@app.route('/projects/export/csv')
@login_required
def export_projects_csv():
    sort_by, sort_order, sort_column, sort_direction = validate_sort(
        request.args.get('sort', 'name'), request.args.get('order', 'asc'),
        {'name': 'p.Pname', 'headcount': 'headcount', 'total_hours': 'total_hours'}
    )

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(Q.get_projects_query(sort_column, sort_direction))
                projects = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
    except Exception as e:
        flash(f'Database error during CSV export: {str(e)}')
        return 'An error occurred during export.', 500

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(column_names)
    writer.writerows(projects)

    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=projects_sorted_export.csv'
    response.mimetype = 'text/csv'
    return response

# -------------------------------------------------------------------------------- #
# ----------------------------------- MANAGERS ----------------------------------- #
# -------------------------------------------------------------------------------- #

@app.route('/managers')
@login_required
def managers():
    current_sort = request.args.get('sort', 'Dnumber')
    current_order = request.args.get('order', 'asc')

    raw_managers = query_all(Q.GET_MANAGERS_WITH_STATS)
    managers = [(dnumber, dname, make_full_name(mfname, mminit, mlname) if mfname else 'N/A', headcount, total_hours)
                for dnumber, dname, mfname, mminit, mlname, headcount, total_hours in raw_managers]

    return render_template('managers/index.html', managers=managers,
                         current_sort=current_sort, current_order=current_order)

# -------------------------------------------------------------------------------- #
# ------------------------------------ OTHER ------------------------------------- #
# -------------------------------------------------------------------------------- #

@app.route('/admin')
@admin_required
def admin():
    users = query_all(Q.GET_ALL_USERS)
    return render_template('auth/admin.html', users=users)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404

if __name__ == '__main__':
    app.run(debug=DEBUG)