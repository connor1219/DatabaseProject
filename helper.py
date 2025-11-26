from flask import session, redirect, url_for, flash
from functools import wraps
from config import DATABASE_CONFIG
import psycopg

def get_db_connection():
    conn = psycopg.connect(**DATABASE_CONFIG)
    return conn

def is_logged_in():
    return 'username' in session

def is_admin():
    return session.get('role') == 'admin'

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_admin():
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper

def validate_registration(username, password, role):
    if not username or not password or not role:
        return False, 'All fields are required'

    username = username.strip()

    if len(username) < 3:
        return False, 'Username must be at least 3 characters'

    if len(username) > 32:
        return False, 'Username must be less than 32 characters'

    if not username.isalnum() and '_' not in username:
        return False, 'Username can only contain letters, numbers, and underscores'

    if len(password) < 6:
        return False, 'Password must be at least 6 characters'

    if len(password) > 32:
        return False, 'Password must be less than 32 characters'

    allowed_roles = ['viewer', 'admin']

    if role not in allowed_roles:
        return False, 'Invalid role selected'

    return True, None

def validate_sort(sort_by, sort_order, allowed_sorts, default='name'):
    allowed_orders = ['asc', 'desc']
    sort_by = sort_by if sort_by in allowed_sorts else default
    sort_order = sort_order.lower() if sort_order.lower() in allowed_orders else 'asc'
    return sort_by, sort_order, allowed_sorts[sort_by], sort_order.upper()

def with_db_cursor(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                return f(conn, cur, *args, **kwargs)
    return wrapper

@with_db_cursor
def query_all(conn, cur, query, args=()):
    cur.execute(query, args)
    return cur.fetchall()

@with_db_cursor
def query_one(conn, cur, query, args=()):
    cur.execute(query, args)
    return cur.fetchone()

@with_db_cursor
def insert(conn, cur, query, args=()):
    try:
        cur.execute(query, args)
        conn.commit()
    except psycopg.OperationalError as e:
        print(f"Database connection failed: {e}")
        raise
    except psycopg.Error as e:
        print(f"Database error: {e}")
        raise

def make_full_name(fname, minit, lname):
    if minit:
        return f"{fname} {minit}. {lname}"
    return f"{fname} {lname}"

def build_employee_list(raw_employees):
    return [(ssn, make_full_name(fname, minit, lname), *rest)
            for ssn, fname, minit, lname, *rest in raw_employees]
