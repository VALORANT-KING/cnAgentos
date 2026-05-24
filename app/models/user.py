import hashlib
import secrets
import sqlite3

from app.models.db import get_connection

def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex()

class UserRepository:
    @staticmethod
    def create_user(username: str, password: str, role: str = "user") -> bool:
        if not username or not password:
            return False
        
        salt = secrets.token_bytes(16)
        password_hash = _hash_password(password, salt)

        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO users(username, password_hash, salt, role) VALUES(?, ?, ?, ?)",
                    (username, password_hash, salt.hex(), role)
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"创建用户失败: {e}")
            return False

    @staticmethod
    def get_user_by_username(username: str) -> dict | None:
        if not username:
            return None
        
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, username, password_hash, salt, role, status FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "salt": row["salt"],
                    "role": row["role"],
                    "status": row["status"]
                }
        return None

    @staticmethod
    def get_user_by_id(user_id: int) -> dict | None:
        if not user_id:
            return None
        
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, username, password_hash, salt, role, status FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "salt": row["salt"],
                    "role": row["role"],
                    "status": row["status"]
                }
        return None

    @staticmethod
    def verify_user(username: str, password: str) -> bool:
        user = UserRepository.get_user_by_username(username)
        if not user:
            return False
        
        if user.get("status") != 1:
            return False
        
        try:
            salt = bytes.fromhex(user["salt"])
            return _hash_password(password, salt) == user["password_hash"]
        except Exception as e:
            print(f"验证用户密码失败: {e}")
            return False

    @staticmethod
    def get_all_users(page: int = 1, page_size: int = 20) -> tuple:
        offset = (page - 1) * page_size
        
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
            
            rows = conn.execute(
                "SELECT id, username, role, status, create_at FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
                (page_size, offset)
            ).fetchall()
            
            users = []
            for row in rows:
                users.append({
                    "id": row["id"],
                    "username": row["username"],
                    "role": row["role"],
                    "status": row["status"],
                    "create_at": row["create_at"]
                })
            
            return users, total

    @staticmethod
    def update_user(user_id: int, password: str = None, role: str = None, status: int = None) -> bool:
        try:
            with get_connection() as conn:
                if password:
                    salt = secrets.token_bytes(16)
                    password_hash = _hash_password(password, salt)
                    conn.execute(
                        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                        (password_hash, salt.hex(), user_id)
                    )
                
                if role is not None:
                    conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
                
                if status is not None:
                    conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
                
                conn.commit()
            return True
        except Exception as e:
            print(f"更新用户失败: {e}")
            return False

    @staticmethod
    def delete_user(user_id: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"删除用户失败: {e}")
            return False

    @staticmethod
    def delete_users_batch(user_ids: list) -> bool:
        if not user_ids:
            return False
        
        try:
            with get_connection() as conn:
                placeholders = ",".join("?" for _ in user_ids)
                conn.execute(f"DELETE FROM users WHERE id IN ({placeholders})", user_ids)
                conn.commit()
            return True
        except Exception as e:
            print(f"批量删除用户失败: {e}")
            return False
