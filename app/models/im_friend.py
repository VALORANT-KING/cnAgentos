from app.models.db import get_connection


class ImFriendRepository:
    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else None

    @staticmethod
    def search_users(keyword, exclude_user_id, limit=20):
        keyword = (keyword or "").strip()
        if not keyword:
            return []
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, username, role, create_at
                FROM users
                WHERE status = 1 AND username LIKE ? AND id != ?
                ORDER BY username LIMIT ?
                """,
                (f"%{keyword}%", exclude_user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def send_request(from_user_id, to_user_id, message=""):
        if from_user_id == to_user_id:
            return False, "不能添加自己为好友"
        with get_connection() as conn:
            if ImFriendRepository.is_friend(from_user_id, to_user_id):
                return False, "已经是好友"
            pending = conn.execute(
                """
                SELECT id FROM im_friend_requests
                WHERE from_user_id = ? AND to_user_id = ? AND status = 0
                """,
                (from_user_id, to_user_id),
            ).fetchone()
            if pending:
                return False, "好友申请已发送，请等待对方处理"
            reverse = conn.execute(
                """
                SELECT id FROM im_friend_requests
                WHERE from_user_id = ? AND to_user_id = ? AND status = 0
                """,
                (to_user_id, from_user_id),
            ).fetchone()
            if reverse:
                return False, "对方已向你发送申请，请在申请列表中处理"
            conn.execute(
                """
                INSERT INTO im_friend_requests(from_user_id, to_user_id, message, status)
                VALUES(?, ?, ?, 0)
                """,
                (from_user_id, to_user_id, message or ""),
            )
            conn.commit()
        return True, "好友申请已发送"

    @staticmethod
    def get_pending_requests(user_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT r.id, r.from_user_id, r.to_user_id, r.message, r.status, r.create_at,
                       u.username AS from_username
                FROM im_friend_requests r
                JOIN users u ON u.id = r.from_user_id
                WHERE r.to_user_id = ? AND r.status = 0
                ORDER BY r.id DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_sent_requests(user_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT r.id, r.from_user_id, r.to_user_id, r.message, r.status, r.create_at,
                       u.username AS to_username
                FROM im_friend_requests r
                JOIN users u ON u.id = r.to_user_id
                WHERE r.from_user_id = ? AND r.status = 0
                ORDER BY r.id DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def accept_request(request_id, user_id):
        with get_connection() as conn:
            req = conn.execute(
                "SELECT * FROM im_friend_requests WHERE id = ? AND to_user_id = ? AND status = 0",
                (request_id, user_id),
            ).fetchone()
            if not req:
                return False, "申请不存在或已处理"
            req = dict(req)
            conn.execute(
                "UPDATE im_friend_requests SET status = 1 WHERE id = ?",
                (request_id,),
            )
            ImFriendRepository._add_friend_pair(conn, req["from_user_id"], req["to_user_id"])
            conn.commit()
        return True, "已添加为好友"

    @staticmethod
    def reject_request(request_id, user_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM im_friend_requests WHERE id = ? AND to_user_id = ? AND status = 0",
                (request_id, user_id),
            ).fetchone()
            if not row:
                return False, "申请不存在或已处理"
            conn.execute(
                "UPDATE im_friend_requests SET status = 2 WHERE id = ?",
                (request_id,),
            )
            conn.commit()
        return True, "已拒绝"

    @staticmethod
    def _add_friend_pair(conn, uid_a, uid_b):
        for u1, u2 in ((uid_a, uid_b), (uid_b, uid_a)):
            exists = conn.execute(
                "SELECT id FROM im_friends WHERE user_id = ? AND friend_id = ? AND status = 1",
                (u1, u2),
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO im_friends(user_id, friend_id, status) VALUES(?, ?, 1)",
                    (u1, u2),
                )

    @staticmethod
    def is_friend(user_id, friend_id):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id FROM im_friends
                WHERE user_id = ? AND friend_id = ? AND status = 1
                """,
                (user_id, friend_id),
            ).fetchone()
            return row is not None

    @staticmethod
    def get_friends(user_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT f.id, f.friend_id, f.remark, f.create_at,
                       u.username, u.id AS user_id
                FROM im_friends f
                JOIN users u ON u.id = f.friend_id
                WHERE f.user_id = ? AND f.status = 1
                ORDER BY u.username
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
