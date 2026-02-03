import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.url import make_url

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sikhiya.db")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

engine_kwargs = {
    "echo": SQL_ECHO,
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)


def should_run_mysql_migrations() -> bool:
    return (
        os.getenv("MIGRATE_DB", "false").lower() == "true"
        and DATABASE_URL.startswith("mysql")
    )


def migrate_mysql_database():
    import pymysql

    url = make_url(DATABASE_URL)
    host = url.host or "localhost"
    user = url.username or "root"
    password = url.password or ""
    port = url.port or 3306
    database = url.database

    if not database:
        print("Skipping migration: DATABASE_URL missing database name")
        return

    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            database=database,
        )
        cursor = connection.cursor()

        cursor.execute("SHOW TABLES LIKE 'users'")
        if cursor.fetchone():
            cursor.execute("SHOW COLUMNS FROM users")
            existing_columns = [col[0] for col in cursor.fetchall()]

            if "role" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'")
                print("Added 'role' column to users table")

            if "reset_otp" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_otp VARCHAR(255) DEFAULT NULL")
                print("Added 'reset_otp' column to users table")
            else:
                cursor.execute("ALTER TABLE users MODIFY COLUMN reset_otp VARCHAR(255) DEFAULT NULL")
                print("Updated 'reset_otp' column size in users table")

            if "otp_expiry" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN otp_expiry DATETIME DEFAULT NULL")
                print("Added 'otp_expiry' column to users table")

            if "board" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN board VARCHAR(100) DEFAULT NULL")
                print("Added 'board' column to users table")

            if "student_class" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN student_class VARCHAR(50) DEFAULT NULL")
                print("Added 'student_class' column to users table")

            if "teacher_status" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN teacher_status VARCHAR(50) DEFAULT NULL")
                print("Added 'teacher_status' column to users table")

            cursor.execute(
                "UPDATE users SET role = 'student' "
                "WHERE role IS NULL OR role = '' OR role = 'user'"
            )
            print("Backfilled legacy roles to 'student'")

            cursor.execute(
                "UPDATE users SET teacher_status = 'pending' "
                "WHERE role = 'teacher' AND (teacher_status IS NULL OR teacher_status = '')"
            )
            print("Backfilled 'teacher_status' for existing teacher accounts")

            connection.commit()

        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Migration handled: {e}")


if should_run_mysql_migrations():
    migrate_mysql_database()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
