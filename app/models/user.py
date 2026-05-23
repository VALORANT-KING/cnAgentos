import hashlib
import secrets
import sqlite3

from app.models.db import get_connection

# 密码加密方法
def _hash_password(password: str, salt: bytes) -> str:
    """
    基于 PBKDF2-HMAC-SHA256 加密密码
    :param password: 原始密码
    :param salt: 盐值（bytes 类型）
    :return: 加密后的密码哈希（16 进制字符串）
    """
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex()

# 用户对象类
class UserRepository:
    # 创建用户方法
    @staticmethod
    def create_user(username: str, password: str) -> bool:
        """
        创建新用户（用户名唯一）
        :param username: 用户名
        :param password: 原始密码
        :return: 创建成功返回 True，用户名重复返回 False
        """
        if not username or not password:
            return False  # 空用户名/密码直接返回失败
        
        salt = secrets.token_bytes(16)
        password_hash = _hash_password(password, salt)

        try:
            with get_connection() as conn:
                # 执行插入操作
                conn.execute(
                    "INSERT INTO users(username, password_hash, salt) VALUES(?, ?, ?)",
                    (username, password_hash, salt.hex())
                )
                conn.commit()  # 确保事务提交（部分 sqlite3 配置需显式提交）
            return True
        except sqlite3.IntegrityError:
            # 用户名重复触发唯一约束错误
            return False
        except Exception as e:
            # 捕获其他数据库异常（可选：可根据需求记录日志）
            print(f"创建用户失败: {e}")
            return False

    # 通过用户名检索用户信息的方法
    @staticmethod
    def get_user_by_username(username: str) -> dict | None:
        """
        根据用户名查询用户信息
        :param username: 用户名
        :return: 用户信息字典（id/username/password_hash/salt），无数据返回 None
        """
        if not username:
            return None
        
        with get_connection() as conn:
            # 设置行工厂，让查询结果返回字典（而非默认元组）
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            
            if row:
                # 转换为字典返回（兼容键值访问）
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "salt": row["salt"]
                }
        return None

    # 验证用户名和密码的方法
    @staticmethod
    def verify_user(username: str, password: str) -> bool:
        """
        验证用户名和密码是否匹配
        :param username: 用户名
        :param password: 原始密码
        :return: 验证通过返回 True，否则返回 False
        """
        user = UserRepository.get_user_by_username(username)
        if not user:
            return False
        
        try:
            # 将盐值从 16 进制字符串转回 bytes
            salt = bytes.fromhex(user["salt"])
            # 重新计算密码哈希并对比
            return _hash_password(password, salt) == user["password_hash"]
        except Exception as e:
            # 盐值解析失败等异常处理
            print(f"验证用户密码失败: {e}")
            return False