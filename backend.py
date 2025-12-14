import sqlite3
import qrcode
from PIL import ImageTk, Image
from datetime import datetime
import os

class Database:
    def __init__(self, db_name="attendance.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                student_name TEXT,
                course_code TEXT,
                room TEXT,
                date_time TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        """)
        self.conn.commit()

    def add_subject(self, name):
        try:
            self.cursor.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
            self.conn.commit()
            return True
        except:
            return False

    def delete_subject(self, name):
        try:
            self.cursor.execute("DELETE FROM subjects WHERE name = ?", (name,))
            self.conn.commit()
            return True
        except:
            return False

    def get_subjects(self):
        self.cursor.execute("SELECT name FROM subjects")
        return [row[0] for row in self.cursor.fetchall()]

    def delete_attendance(self, record_id):
        try:
            self.cursor.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
            self.conn.commit()
            return True
        except:
            return False

    def get_subject_stats(self, course_code):
        # Returns [ (student_name, count) ] ordered by count desc
        if not course_code: return []
        self.cursor.execute("""
            SELECT student_name, COUNT(*) as c 
            FROM attendance 
            WHERE course_code = ? 
            GROUP BY student_id 
            ORDER BY c DESC
        """, (course_code,))
        return self.cursor.fetchall()

    def check_duplicate(self, student_id, course_code, date_str):
        # Check if this student has already checked in for this course on this date (ignoring time for simplicity, or just duplicate record)
        # We'll check if a record exists for this student_id and course_code on the same "date" part of date_time
        query = "SELECT * FROM attendance WHERE student_id = ? AND course_code = ? AND date_time LIKE ?"
        self.cursor.execute(query, (student_id, course_code, f"{date_str}%"))
        return self.cursor.fetchone() is not None

    def save_attendance(self, student_id, student_name, course_code, room):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        full_datetime = f"{date_str} {time_str}"

        if self.check_duplicate(student_id, course_code, date_str):
            return False, "ເຊັກຊື່ຊ້ຳ (Duplicate Check-in)"

        try:
            self.cursor.execute("""
                INSERT INTO attendance (student_id, student_name, course_code, room, date_time)
                VALUES (?, ?, ?, ?, ?)
            """, (student_id, student_name, course_code, room, full_datetime))
            self.conn.commit()
            return True, f"ເຊັກຊື່ສຳເລັດເວລາ {time_str}"
        except Exception as e:
            return False, str(e)

    def get_attendance_by_date(self, date_str, subject=None):
        if subject:
            self.cursor.execute("SELECT * FROM attendance WHERE date_time LIKE ? AND course_code = ?", (f"{date_str}%", subject))
        else:
            self.cursor.execute("SELECT * FROM attendance WHERE date_time LIKE ?", (f"{date_str}%",))
        return self.cursor.fetchall()

    def get_student_stats(self, student_id):
        self.cursor.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (student_id,))
        return self.cursor.fetchone()[0]

    def close(self):
        self.conn.close()

def generate_qr_image(data):
    # Create QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    return img
