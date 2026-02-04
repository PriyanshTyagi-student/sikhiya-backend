import os
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel
from datetime import datetime, timedelta
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from database import engine, Base, SessionLocal
import models
from models import User, Course  # Import User model from models.py
try:
    from admin_config import ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME
except Exception:
    ADMIN_EMAIL = "admin@sikhiya.com"
    ADMIN_PASSWORD = "admin123"
    ADMIN_NAME = "Sikhiya Admin"

# Create tables if they don't exist, skip if they already exist
try:
    Base.metadata.create_all(bind=engine, checkfirst=True)
except Exception as e:
    print(f"Table creation handled: {e}")

MAIL_USERNAME = os.getenv("MAIL_USERNAME", "sikhiyaconnect@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "eobq tpxi xydz uyiz")
MAIL_FROM = os.getenv("MAIL_FROM", "sikhiyaconnect@gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "true").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"

conf = None
if MAIL_USERNAME and MAIL_PASSWORD and MAIL_FROM:
    conf = ConnectionConfig(
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_FROM=MAIL_FROM,
        MAIL_PORT=MAIL_PORT,
        MAIL_SERVER=MAIL_SERVER,
        MAIL_STARTTLS=MAIL_STARTTLS,
        MAIL_SSL_TLS=MAIL_SSL_TLS,
    )


# -------------------- CONFIG --------------------

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_LATER")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# -------------------- APP --------------------

app = FastAPI(title="Sikhiya Connect Backend")

cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
cors_origins = ["*"] if cors_origins_raw.strip() == "*" else [
    origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- DATABASE --------------------
# MySQL Database configuration is imported from database.py
# SessionLocal and engine are already imported from database module

# -------------------- SECURITY --------------------

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

def is_admin_credentials(email: str, password: str):
    return email == ADMIN_EMAIL and password == ADMIN_PASSWORD

def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {**data, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
import random
import hashlib
import secrets

def generate_otp():
    return str(random.randint(100000, 999999))

def hash_otp(otp: str):
    return hashlib.sha256(otp.encode()).hexdigest()

def verify_otp(plain_otp: str, hashed_otp: str):
    return hash_otp(plain_otp) == hashed_otp

def generate_temp_password(length: int = 10):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))

# -------------------- MODELS --------------------
# User model is imported from models.py


# -------------------- SCHEMAS --------------------

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str
    board: str = None  # For students
    student_class: str = None  # For students

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateCourseRequest(BaseModel):
    title: str
    description: str = None
    level: str = "beginner"
    duration: int = 0
    thumbnail: str = None
    target_class: str = None  # e.g., "Class 5", "6-8", "9-10", "11-12"
    target_board: str = None  # e.g., "PSEB", "CBSE", "ICSE", "All"

# -------------------- DEPENDENCY --------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------- ROUTES --------------------

@app.get("/")
def read_root():
    return {"status": "online", "message": "Sikhiya Connect API is running"}

@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
        role=data.role,
        board=data.board if data.role == "student" else None,
        student_class=data.student_class if data.role == "student" else None,
        teacher_status="pending" if data.role == "teacher" else None,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User registered"}

@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    if is_admin_credentials(data.email, data.password):
        token = create_access_token({
            "user_id": 0,
            "email": ADMIN_EMAIL,
            "role": "admin",
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": "admin-001",
                "name": ADMIN_NAME,
                "email": ADMIN_EMAIL,
                "role": "admin",
            }
        }

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "board": user.board,
            "student_class": user.student_class,
            "teacherStatus": user.teacher_status,
        }
    }

# -------------------- FORGOT PASSWORD --------------------
class ForgotPasswordRequest(BaseModel):
    email: str

@app.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    if conf is None:
        raise HTTPException(status_code=500, detail="Email service not configured")

    otp = generate_otp()
    user.reset_otp = hash_otp(otp)
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    db.commit()

    message = MessageSchema(
        subject="Sikhiya Connect - Password Reset OTP",
        recipients=[user.email],
        body=f"Your OTP is {otp}. It expires in 10 minutes.",
        subtype="plain",
    )

    fm = FastMail(conf)
    await fm.send_message(message)

    return {"message": "OTP sent to email"}

# -------------------- VERIFY OTP --------------------
class VerifyOtpRequest(BaseModel):
    email: str
    otp: str

@app.post("/verify-otp")
def verify_otp_api(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.reset_otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if user.otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    if not verify_otp(data.otp, user.reset_otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    return {"message": "OTP verified"}

# -------------------- RESET PASSWORD --------------------
class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str

@app.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.reset_otp:
        raise HTTPException(status_code=400, detail="Invalid request")

    user.password = hash_password(data.new_password)
    user.reset_otp = None
    user.otp_expiry = None

    db.commit()
    return {"message": "Password reset successful"}

# -------------------- DASHBOARD --------------------

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Extract user from JWT token in Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        # Extract token from "Bearer TOKEN" format
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = parts[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def get_current_admin(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        token = parts[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"email": payload.get("email"), "role": role}

def get_current_teacher(user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    if user.teacher_status != "approved":
        raise HTTPException(status_code=403, detail="Teacher not approved")
    return user

@app.get("/admin/students")
def get_admin_students(admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    students = db.query(User).filter(User.role.in_(["student", "user"])).all()
    return {
        "students": [
            {
                "id": s.id,
                "name": s.name,
                "email": s.email,
                "role": s.role,
                "board": s.board,
                "student_class": s.student_class,
                "avatar": s.name[0].upper() if s.name else "?",
            }
            for s in students
        ]
    }

@app.get("/teacher/courses")
def get_teacher_courses(teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()
    return {
        "courses": [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "level": c.level,
                "duration": c.duration_hours,
                "teacherId": c.teacher_id,
                "teacherName": teacher.name,
                "modules": [],
                "thumbnail": c.thumbnail,
                "target_class": c.target_class,
                "target_board": c.target_board,
                "createdAt": c.created_at,
                "studentCount": 0,
            }
            for c in courses
        ]
    }

@app.post("/teacher/courses")
def create_teacher_course(data: CreateCourseRequest, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    course = Course(
        title=data.title,
        description=data.description,
        level=data.level,
        duration_hours=data.duration,
        thumbnail=data.thumbnail,
        teacher_id=teacher.id,
        target_class=data.target_class,
        target_board=data.target_board,
        created_at=datetime.utcnow(),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "level": course.level,
            "duration": course.duration_hours,
            "target_class": course.target_class,
            "target_board": course.target_board,
            "teacherId": course.teacher_id,
            "teacherName": teacher.name,
            "modules": [],
            "thumbnail": course.thumbnail,
            "createdAt": course.created_at,
            "studentCount": 0,
        }
    }

@app.get("/teacher/courses/{course_id}")
def get_teacher_course(course_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "level": course.level,
        "duration_hours": course.duration_hours,
        "thumbnail": course.thumbnail,
        "target_class": course.target_class,
        "target_board": course.target_board,
        "teacher_id": course.teacher_id,
        "created_at": course.created_at,
    }

@app.put("/teacher/courses/{course_id}")
def update_teacher_course(course_id: int, data: CreateCourseRequest, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course.title = data.title
    course.description = data.description
    course.level = data.level
    course.duration_hours = data.duration
    if data.thumbnail:
        course.thumbnail = data.thumbnail
    course.target_class = data.target_class
    course.target_board = data.target_board
    
    db.commit()
    db.refresh(course)
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "level": course.level,
        "duration_hours": course.duration_hours,
        "thumbnail": course.thumbnail,
        "target_class": course.target_class,
        "target_board": course.target_board,
        "teacher_id": course.teacher_id,
        "created_at": course.created_at,
    }

@app.delete("/teacher/courses/{course_id}")
def delete_teacher_course(course_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(course)
    db.commit()
    
    return {"message": "Course deleted successfully"}

@app.get("/teacher/students")
def get_teacher_students(teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Get all students enrolled in the teacher's courses"""
    # For now, return all students since we don't have enrollment tracking yet
    # In production, this would query a student_enrollments table
    students = db.query(User).filter(
        User.role.in_(["student", "user"])
    ).all()
    
    return {
        "students": [
            {
                "id": s.id,
                "name": s.name,
                "email": s.email,
                "board": s.board,
                "student_class": s.student_class,
                "enrolledCourses": 0,  # TODO: Count from enrollments table
            }
            for s in students
        ]
    }

@app.get("/teacher/dashboard")
def get_teacher_dashboard(teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Get teacher dashboard stats from database"""
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()
    total_courses = len(courses)

    # Enrollment tracking not implemented yet
    total_enrollments = 0
    total_students = 0

    # Weekly counts based on course creation dates (placeholder for enrollments)
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=6)
    counts = {}
    for course in courses:
        if course.created_at:
            course_date = course.created_at.date()
            if course_date >= start_date and course_date <= today:
                counts[course_date] = counts.get(course_date, 0) + 1

    weekly_enrollments = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        weekly_enrollments.append({
            "day": day.strftime("%a"),
            "hours": counts.get(day, 0)
        })

    return {
        "stats": {
            "totalCourses": total_courses,
            "totalStudents": total_students,
            "totalEnrollments": total_enrollments,
        },
        "weeklyEnrollments": weekly_enrollments,
        "questions": []
    }

@app.get("/admin/teachers")
def get_admin_teachers(status: str = None, admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == "teacher")
    if status:
        query = query.filter(User.teacher_status == status)
    teachers = query.all()
    return {
        "teachers": [
            {
                "id": t.id,
                "name": t.name,
                "email": t.email,
                "role": t.role,
                "teacherStatus": t.teacher_status,
                "avatar": t.name[0].upper() if t.name else "?",
                "bio": None,
                "qualifications": None,
            }
            for t in teachers
        ]
    }

@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int, admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    
    # If teacher, delete their courses first (cascade delete)
    if user.role == "teacher":
        courses = db.query(Course).filter(Course.teacher_id == user_id).all()
        for course in courses:
            # Delete related resources
            db.query(CourseResource).filter(CourseResource.course_id == course.id).delete()
            # Delete lesson progress
            db.query(StudentLessonProgress).filter(
                StudentLessonProgress.lesson_id.in_(
                    db.query(CourseLesson.id).filter(
                        CourseLesson.module_id.in_(
                            db.query(CourseModule.id).filter(CourseModule.course_id == course.id)
                        )
                    )
                )
            ).delete()
            # Delete lessons
            db.query(CourseLesson).filter(
                CourseLesson.module_id.in_(
                    db.query(CourseModule.id).filter(CourseModule.course_id == course.id)
                )
            ).delete()
            # Delete modules
            db.query(CourseModule).filter(CourseModule.course_id == course.id).delete()
            # Delete enrollments
            db.query(StudentCourseEnrollment).filter(StudentCourseEnrollment.course_id == course.id).delete()
            # Delete the course
            db.delete(course)
    
    # Delete student enrollments
    db.query(StudentCourseEnrollment).filter(StudentCourseEnrollment.student_id == user_id).delete()
    # Delete lesson progress
    db.query(StudentLessonProgress).filter(StudentLessonProgress.student_id == user_id).delete()
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

@app.post("/admin/users/{user_id}/reset-password")
def reset_user_password(user_id: int, admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot reset admin password")

    temp_password = generate_temp_password()
    user.password = hash_password(temp_password)
    user.reset_otp = None
    user.otp_expiry = None
    db.commit()
    return {"message": "Password reset", "temporaryPassword": temp_password}

@app.post("/admin/teachers/{teacher_id}/approve")
def approve_teacher(teacher_id: int, admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    teacher.teacher_status = "approved"
    db.commit()
    return {"message": "Teacher approved"}

@app.post("/admin/teachers/{teacher_id}/reject")
def reject_teacher(teacher_id: int, admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    teacher.teacher_status = "rejected"
    db.commit()
    return {"message": "Teacher rejected"}

@app.get("/dashboard")
def get_dashboard(user: User = Depends(get_current_user)):
    """Get dashboard data for authenticated user"""
    # For new students (no enrollment data), return zero stats
    # In production, this would query a student_courses table
    # For now, demo users get sample data
    
    is_demo_user = user.email in ["priya@sikhiya.com", "rajesh@sikhiya.com", "aisha@sikhiya.com"]
    
    if is_demo_user:
        # Demo users see sample courses
        enrolled_courses = ["course1", "course2", "course3"]
        course_progress = {"course1": 75, "course2": 50, "course3": 30}
        stats = {
            "coursesEnrolled": 3,
            "hoursLearned": 42,
            "currentStreak": 7,
            "completedCourses": 1,
        }
    else:
        # New students see empty dashboard
        enrolled_courses = []
        course_progress = {}
        stats = {
            "coursesEnrolled": 0,
            "hoursLearned": 0,
            "currentStreak": 0,
            "completedCourses": 0,
        }
    
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "stats": stats,
        "enrolledCourses": enrolled_courses,
        "courseProgress": course_progress,
        "weeklyActivity": [
            {"day": "Mon", "hours": 2},
            {"day": "Tue", "hours": 3},
            {"day": "Wed", "hours": 1},
            {"day": "Thu", "hours": 4},
            {"day": "Fri", "hours": 2},
            {"day": "Sat", "hours": 5},
            {"day": "Sun", "hours": 0},
        ]
    }

# -------------------- COURSE CONTENT MANAGEMENT --------------------

@app.get("/teacher/courses/{course_id}/modules")
def get_course_modules(course_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Get all modules for a course"""
    from models import CourseModule, CourseLesson
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    modules = db.query(CourseModule).filter(CourseModule.course_id == course_id).order_by(CourseModule.order).all()
    
    result = []
    for module in modules:
        lessons = db.query(CourseLesson).filter(CourseLesson.module_id == module.id).order_by(CourseLesson.order).all()
        result.append({
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "lessons": [
                {
                    "id": l.id,
                    "title": l.title,
                    "video_file": l.video_file,
                    "duration_seconds": l.duration_seconds,
                }
                for l in lessons
            ]
        })
    
    return {"modules": result}

@app.post("/teacher/courses/{course_id}/modules")
def create_course_module(course_id: int, title: str = None, description: str = None, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Create a module for a course"""
    from models import CourseModule
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Parse JSON body
    import json
    
    module = CourseModule(
        course_id=course_id,
        title=title or "Untitled Module",
        description=description,
        order=0,
        created_at=datetime.utcnow(),
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    
    return {
        "id": module.id,
        "title": module.title,
        "description": module.description,
    }

@app.post("/teacher/courses/{course_id}/modules/{module_id}/lessons")
def create_lesson(
    course_id: int,
    module_id: int,
    title: str = None,
    teacher: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Create a lesson in a module"""
    from models import CourseModule, CourseLesson
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    module = db.query(CourseModule).filter(CourseModule.id == module_id, CourseModule.course_id == course_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    lesson = CourseLesson(
        module_id=module_id,
        title=title or "Untitled Lesson",
        duration_seconds=0,
        order=0,
        created_at=datetime.utcnow(),
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    
    return {
        "id": lesson.id,
        "title": lesson.title,
        "duration_seconds": lesson.duration_seconds,
    }

@app.get("/teacher/courses/{course_id}/resources")
def get_course_resources(course_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Get all resources for a course"""
    from models import CourseResource
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    resources = db.query(CourseResource).filter(CourseResource.course_id == course_id).all()
    
    return {
        "resources": [
            {
                "id": r.id,
                "title": r.title,
                "file_type": r.file_type,
                "size_mb": r.size_mb,
            }
            for r in resources
        ]
    }

@app.post("/teacher/courses/{course_id}/resources")
def upload_course_resource(course_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Upload a resource for a course (placeholder)"""
    from models import CourseResource
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Placeholder for file upload
    resource = CourseResource(
        course_id=course_id,
        title="Sample Resource",
        file_path="/uploads/sample.zip",
        file_type="zip",
        size_mb=5.0,
        created_at=datetime.utcnow(),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    return {
        "resource": {
            "id": resource.id,
            "title": resource.title,
            "file_type": resource.file_type,
            "size_mb": resource.size_mb,
        }
    }

@app.delete("/teacher/courses/{course_id}/resources/{resource_id}")
def delete_course_resource(course_id: int, resource_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Delete a course resource"""
    from models import CourseResource
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    resource = db.query(CourseResource).filter(
        CourseResource.id == resource_id,
        CourseResource.course_id == course_id
    ).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    db.delete(resource)
    db.commit()
    
    return {"message": "Resource deleted successfully"}

# -------------------- STUDENT COURSE BROWSING --------------------

def check_course_access(user: User, course: Course) -> bool:
    """Check if a student can access a course based on their class and board"""
    if not user.student_class:
        return False
    
    # Check board
    if course.target_board and course.target_board != "All" and course.target_board != user.board:
        return False
    
    # Check class
    if course.target_class:
        student_class = int(user.student_class) if user.student_class.isdigit() else 0
        
        if "-" in course.target_class:
            # Range like "6-8" or "9-10"
            start, end = course.target_class.split("-")
            start, end = int(start), int(end)
            if not (start <= student_class <= end):
                return False
        else:
            # Specific class like "Class 5"
            if student_class != int(course.target_class.split()[-1]):
                return False
    
    return True

@app.get("/courses/available")
def get_available_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get courses available for the current student based on their class"""
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")
    
    courses = db.query(Course).all()
    available = []
    
    for course in courses:
        if check_course_access(user, course):
            teacher = db.query(User).filter(User.id == course.teacher_id).first()
            available.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "level": course.level,
                "duration_hours": course.duration_hours,
                "thumbnail": course.thumbnail,
                "target_class": course.target_class,
                "target_board": course.target_board,
                "teacher_id": course.teacher_id,
                "teacher_name": teacher.name if teacher else "Unknown",
                "created_at": course.created_at,
            })
    
    return {"courses": available, "count": len(available)}

@app.post("/courses/{course_id}/enroll")
def request_enrollment(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Request to enroll in a course (requires teacher approval)"""
    from models import StudentCourseEnrollment
    
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can enroll")
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if student can access this course
    if not check_course_access(user, course):
        raise HTTPException(status_code=403, detail="Course is not available for your class/board")
    
    # Check if already requested or enrolled
    existing = db.query(StudentCourseEnrollment).filter(
        StudentCourseEnrollment.student_id == user.id,
        StudentCourseEnrollment.course_id == course_id
    ).first()
    
    if existing:
        if existing.status == "pending":
            raise HTTPException(status_code=400, detail="You have already requested to enroll in this course")
        elif existing.status == "approved":
            raise HTTPException(status_code=400, detail="Already enrolled in this course")
        elif existing.status == "rejected":
            raise HTTPException(status_code=400, detail="Your enrollment request was rejected")
    
    enrollment = StudentCourseEnrollment(
        student_id=user.id,
        course_id=course_id,
        enrolled_at=datetime.utcnow(),
        status="pending"  # Changed to pending - requires teacher approval
    )
    db.add(enrollment)
    db.commit()
    
    return {"message": "Enrollment request sent to teacher", "enrollment_id": enrollment.id, "status": "pending"}

@app.post("/courses/{course_id}/enrollment/{enrollment_id}/approve")
def approve_enrollment(course_id: int, enrollment_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Teacher approves student enrollment request"""
    from models import StudentCourseEnrollment
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    enrollment = db.query(StudentCourseEnrollment).filter(
        StudentCourseEnrollment.id == enrollment_id,
        StudentCourseEnrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment request not found")
    
    enrollment.status = "approved"
    db.commit()
    
    return {"message": "Enrollment approved"}

@app.post("/courses/{course_id}/enrollment/{enrollment_id}/reject")
def reject_enrollment(course_id: int, enrollment_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Teacher rejects student enrollment request"""
    from models import StudentCourseEnrollment
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    enrollment = db.query(StudentCourseEnrollment).filter(
        StudentCourseEnrollment.id == enrollment_id,
        StudentCourseEnrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment request not found")
    
    enrollment.status = "rejected"
    db.commit()
    
    return {"message": "Enrollment rejected"}

@app.post("/courses/{course_id}/unenroll")
def unenroll_from_course(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Student unenrolls from a course"""
    from models import StudentCourseEnrollment
    
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can unenroll")
    
    enrollment = db.query(StudentCourseEnrollment).filter(
        StudentCourseEnrollment.student_id == user.id,
        StudentCourseEnrollment.course_id == course_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    db.delete(enrollment)
    db.commit()
    
    return {"message": "Successfully unenrolled from course"}


@app.get("/student/enrollments")
def get_student_enrollments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all courses the student is enrolled in"""
    from models import StudentCourseEnrollment
    
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    enrollments = db.query(StudentCourseEnrollment).filter(StudentCourseEnrollment.student_id == user.id).all()
    
    courses = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if course:
            teacher = db.query(User).filter(User.id == course.teacher_id).first()
            courses.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "level": course.level,
                "duration_hours": course.duration_hours,
                "thumbnail": course.thumbnail,
                "teacher_name": teacher.name if teacher else "Unknown",
                "enrolled_at": enrollment.enrolled_at,
                "status": enrollment.status,
            })
    
    return {"courses": courses, "count": len(courses)}

@app.get("/teacher/courses/{course_id}/enrollment-requests")
def get_enrollment_requests(course_id: int, teacher: User = Depends(get_current_teacher), db: Session = Depends(get_db)):
    """Get pending enrollment requests for a course"""
    from models import StudentCourseEnrollment
    
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    enrollments = db.query(StudentCourseEnrollment).filter(
        StudentCourseEnrollment.course_id == course_id,
        StudentCourseEnrollment.status == "pending"
    ).all()
    
    requests = []
    for enrollment in enrollments:
        student = db.query(User).filter(User.id == enrollment.student_id).first()
        if student:
            requests.append({
                "enrollment_id": enrollment.id,
                "student_id": student.id,
                "student_name": student.name,
                "student_email": student.email,
                "requested_at": enrollment.enrolled_at,
                "status": enrollment.status,
            })
    
    return {"requests": requests, "count": len(requests)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
