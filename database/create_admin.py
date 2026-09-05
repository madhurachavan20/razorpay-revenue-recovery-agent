from database.db import get_connection
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


EMAIL = "admin@revenueos.com"
PASSWORD = "admin123"
NAME = "RevenueOS Admin"


def create_admin():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        hashed_password = password_hash.hash(PASSWORD)

        cursor.execute(
            """
            INSERT INTO users (
                email,
                password_hash,
                name,
                role
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email)
            DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                name = EXCLUDED.name,
                role = EXCLUDED.role
            """,
            (
                EMAIL,
                hashed_password,
                NAME,
                "ADMIN",
            ),
        )

        connection.commit()

        print("================================")
        print("RevenueOS admin user created")
        print("Email:    admin@revenueos.com")
        print("Password: admin123")
        print("================================")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    create_admin()