from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    reset_otp = Column(String(255), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    board = Column(String(100), nullable=True)  # Student board (e.g., "PSEB", "Other")
    student_class = Column(String(50), nullable=True)  # Student class (e.g., "1", "10")
    teacher_status = Column(String(50), nullable=True)  # pending | approved | rejected


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(String(50), nullable=False, default="beginner")
    duration_hours = Column(Integer, nullable=False, default=0)
    thumbnail = Column(String(255), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_class = Column(String(50), nullable=True)  # e.g., "1-5", "6-8", "9-10", "11-12", or specific "Class 5"
    target_board = Column(String(100), nullable=True)  # e.g., "PSEB", "CBSE", "ICSE" or "All"
    created_at = Column(DateTime, nullable=False)


class CourseModule(Base):
    __tablename__ = "course_modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)


class CourseLesson(Base):
    __tablename__ = "course_lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("course_modules.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    video_file = Column(String(500), nullable=True)  # Path to video file
    duration_seconds = Column(Integer, nullable=False, default=0)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)


class CourseResource(Base):
    __tablename__ = "course_resources"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, zip, doc, etc.
    size_mb = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)


class StudentCourseEnrollment(Base):
    __tablename__ = "student_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False, default="active")  # active, completed, dropped


class StudentLessonProgress(Base):
    __tablename__ = "lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("course_lessons.id"), nullable=False)
    watched_seconds = Column(Integer, nullable=False, default=0)  # How far student watched
    completed = Column(Integer, nullable=False, default=0)  # 1 if completed, 0 otherwise
    last_accessed = Column(DateTime, nullable=True)
