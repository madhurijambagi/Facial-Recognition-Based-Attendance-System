-- Facial Recognition Attendance System — database schema
--
-- The rest of this project assumed these tables already existed but never
-- shipped a script to create them. This file fills that gap: it matches the
-- exact columns the application queries in app.py.
--
-- Usage:
--   mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS facial_attendance_mini_project
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE facial_attendance_mini_project;

CREATE TABLE IF NOT EXISTS teacher (
    teacher_id    VARCHAR(20)  PRIMARY KEY,
    TEACHER_CODE  VARCHAR(50)  NOT NULL,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS student (
    student_id    INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    reg_no        VARCHAR(50),
    course        VARCHAR(100),
    semester      INT,
    is_active     TINYINT(1) NOT NULL DEFAULT 1,
    face_encoding BLOB NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS subject (
    subject_id    INT AUTO_INCREMENT PRIMARY KEY,
    subject_name  VARCHAR(100) NOT NULL,
    semester      INT,
    course        VARCHAR(100)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS teacher_subject (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id    VARCHAR(20) NOT NULL,
    subject_id    INT NOT NULL,
    class_id      VARCHAR(50),
    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subject(subject_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id    INT AUTO_INCREMENT PRIMARY KEY,
    student_id       INT NOT NULL,
    subject_id       INT NOT NULL,
    teacher_id       VARCHAR(20) NOT NULL,
    attendance_date  DATE NOT NULL,
    attendance_time  TIME NOT NULL,
    status           ENUM('Present','Absent') NOT NULL DEFAULT 'Present',
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subject(subject_id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id) ON DELETE CASCADE,
    UNIQUE KEY uniq_attendance_per_day (student_id, subject_id, attendance_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(150) NOT NULL UNIQUE,
    password      VARCHAR(255) NOT NULL,   -- a werkzeug password hash, never plaintext
    role          ENUM('admin','teacher','student') NOT NULL,
    reference_id  VARCHAR(20) NOT NULL     -- teacher_id or student_id, stored as text
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Bootstrap admin account
-- /add_teacher (and other admin actions) now require an authenticated admin
-- session, and there is no public signup flow for the first admin. Generate
-- a real password hash first:
--
--   python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password-here'))"
--
-- then paste the result below and run this INSERT manually — do not commit
-- a real password hash to version control.
-- ---------------------------------------------------------------------------
-- INSERT INTO users (email, password, role, reference_id)
-- VALUES ('admin@example.com', '<paste-generated-hash-here>', 'admin', '0');
