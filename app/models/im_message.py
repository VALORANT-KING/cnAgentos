from app.models.db import get_connection


class ImMessageRepository:
    @staticmethod
    def add(sender_id, receiver_type, receiver_id, content, msg_type="text",
            file_path="", file_id=0, employee_id=0):
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO im_messages(
                    msg_type, content, file_path, file_id, sender_id,
                    receiver_type, receiver_id, employee_id
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_type, content or "", file_path or "", file_id,
                    sender_id, receiver_type, receiver_id, employee_id,
                ),
            )
            msg_id = cur.lastrowid
            conn.commit()
        return ImMessageRepository.get_by_id(msg_id)

    @staticmethod
    def _sender_sql():
        return """
            SELECT m.*,
                   CASE WHEN m.sender_id = 0 THEN COALESCE(de.name, '数字员工')
                        ELSE u.username END AS sender_name
            FROM im_messages m
            LEFT JOIN users u ON u.id = m.sender_id AND m.sender_id > 0
            LEFT JOIN digital_employees de ON de.id = m.employee_id AND m.sender_id = 0
        """

    @staticmethod
    def get_by_id(msg_id):
        with get_connection() as conn:
            row = conn.execute(
                ImMessageRepository._sender_sql() + " WHERE m.id = ?",
                (msg_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_history(user_id, receiver_type, receiver_id, limit=50, before_id=0):
        base = ImMessageRepository._sender_sql()
        if receiver_type == "user":
            sql = base + """
                WHERE (
                    (m.sender_id = ? AND m.receiver_type = 'user' AND m.receiver_id = ?)
                    OR (m.sender_id = ? AND m.receiver_type = 'user' AND m.receiver_id = ?)
                )
            """
            params = [user_id, receiver_id, receiver_id, user_id]
        else:
            sql = base + """
                WHERE m.receiver_type = 'group' AND m.receiver_id = ?
            """
            params = [receiver_id]

        if before_id:
            sql += " AND m.id < ?"
            params.append(before_id)
        sql += " ORDER BY m.id DESC LIMIT ?"
        params.append(limit)

        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            items = [dict(r) for r in rows]
            items.reverse()
            return items

    @staticmethod
    def get_recent_conversations(user_id, limit=30):
        """最近会话摘要（好友+群）"""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.receiver_type, m.receiver_id, m.content, m.msg_type,
                       m.create_at, m.sender_id,
                       CASE
                         WHEN m.receiver_type = 'user' AND m.sender_id = ?
                           THEN m.receiver_id
                         WHEN m.receiver_type = 'user'
                           THEN m.sender_id
                         ELSE m.receiver_id
                       END AS peer_id,
                       CASE WHEN m.receiver_type = 'group' THEN g.name
                            ELSE u.username END AS peer_name
                FROM im_messages m
                LEFT JOIN users u ON u.id = (
                    CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END
                ) AND m.receiver_type = 'user'
                LEFT JOIN im_groups g ON g.id = m.receiver_id AND m.receiver_type = 'group'
                WHERE m.id IN (
                    SELECT MAX(id) FROM im_messages
                    WHERE sender_id = ? OR (
                        receiver_type = 'user' AND receiver_id = ?
                    ) OR (
                        receiver_type = 'group' AND receiver_id IN (
                            SELECT group_id FROM im_group_members WHERE user_id = ?
                        )
                    )
                    GROUP BY receiver_type,
                    CASE WHEN receiver_type = 'user' THEN
                        CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END
                    ELSE receiver_id END
                )
                ORDER BY m.id DESC LIMIT ?
                """,
                (user_id, user_id, user_id, user_id, user_id, user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
