CREATE TABLE app_user (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN (’admin’,’viewer’))
);

CREATE INDEX idx_employee_name ON Employee (Lname, Fname, Minit);
CREATE INDEX idx_department_dno ON Department (Dno);