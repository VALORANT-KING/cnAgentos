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
    def get_ai_context(user_id, receiver_type, receiver_id, limit=10):
        """获取与数字员工相关的多轮对话上下文"""
        base = ImMessageRepository._sender_sql()
        if receiver_type == "user":
            sql = base + """
                WHERE m.receiver_type = 'user' AND (
                    (m.sender_id = ? AND m.receiver_id = ?)
                    OR (m.sender_id = ? AND m.receiver_id = ?)
                ) AND m.msg_type IN ('text', 'employee_call')
            """
            params = [user_id, receiver_id, receiver_id, user_id]
        else:
            sql = base + """
                WHERE m.receiver_type = 'group' AND m.receiver_id = ?
                AND m.msg_type IN ('text', 'employee_call')
            """
            params = [receiver_id]
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

    @staticmethod
    def _admin_list_filters(
        receiver_type=None,
        keyword=None,
        username=None,
        group_keyword=None,
        user_id=0,
        group_id=0,
    ):
        where = ["1=1"]
        params = []
        if receiver_type in ("user", "group"):
            where.append("m.receiver_type = ?")
            params.append(receiver_type)
        if keyword:
            where.append("m.content LIKE ?")
            params.append(f"%{keyword}%")
        if group_id:
            where.append("m.receiver_type = 'group' AND m.receiver_id = ?")
            params.append(group_id)
        elif group_keyword:
            where.append(
                "m.receiver_type = 'group' AND m.receiver_id IN "
                "(SELECT id FROM im_groups WHERE name LIKE ?)"
            )
            params.append(f"%{group_keyword}%")
        if user_id:
            where.append(
                """
                (
                    m.sender_id = ?
                    OR (m.receiver_type = 'user' AND m.receiver_id = ?)
                    OR (
                        m.receiver_type = 'group'
                        AND m.receiver_id IN (
                            SELECT group_id FROM im_group_members WHERE user_id = ?
                        )
                    )
                )
                """
            )
            params.extend([user_id, user_id, user_id])
        elif username:
            like = f"%{username}%"
            where.append(
                """
                (
                    m.sender_id IN (SELECT id FROM users WHERE username LIKE ?)
                    OR (
                        m.receiver_type = 'user'
                        AND m.receiver_id IN (SELECT id FROM users WHERE username LIKE ?)
                    )
                )
                """
            )
            params.extend([like, like])
        return " AND ".join(where), params

    @staticmethod
    def admin_list(
        page=1,
        limit=20,
        receiver_type=None,
        keyword=None,
        username=None,
        group_keyword=None,
        user_id=0,
        group_id=0,
    ):
        where_clause, params = ImMessageRepository._admin_list_filters(
            receiver_type, keyword, username, group_keyword, user_id, group_id
        )
        offset = (page - 1) * limit
        with get_connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS c FROM im_messages m WHERE {where_clause}",
                params,
            ).fetchone()["c"]
            rows = conn.execute(
                ImMessageRepository._admin_list_sql() + f" WHERE {where_clause} "
                "ORDER BY m.id DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            items = [ImMessageRepository._admin_enrich_row(dict(r)) for r in rows]
            return items, total

    @staticmethod
    def _admin_list_sql():
        return """
            SELECT m.*,
                   CASE WHEN m.sender_id = 0 THEN COALESCE(de.name, '数字员工')
                        ELSE su.username END AS sender_name,
                   CASE WHEN m.receiver_type = 'group' THEN g.name
                        WHEN m.sender_id = 0 THEN ru.username
                        WHEN m.receiver_id = 0 THEN su.username
                        ELSE su.username || ' ↔ ' || ru.username END AS conversation_name,
                   CASE WHEN m.receiver_type = 'group' THEN '群聊' ELSE '私聊' END AS chat_type,
                   ru.username AS receiver_username,
                   g.name AS group_name
            FROM im_messages m
            LEFT JOIN users su ON su.id = m.sender_id AND m.sender_id > 0
            LEFT JOIN users ru ON ru.id = m.receiver_id AND m.receiver_type = 'user'
            LEFT JOIN im_groups g ON g.id = m.receiver_id AND m.receiver_type = 'group'
            LEFT JOIN digital_employees de ON de.id = m.employee_id AND m.sender_id = 0
        """

    @staticmethod
    def _admin_enrich_row(row):
        if row.get("receiver_type") == "group":
            row["view_receiver_type"] = "group"
            row["view_receiver_id"] = row["receiver_id"]
            row["view_peer_user_id"] = 0
            row["view_user_id"] = 0
        else:
            row["view_receiver_type"] = "user"
            sid = int(row.get("sender_id") or 0)
            rid = int(row.get("receiver_id") or 0)
            if sid > 0:
                row["view_user_id"] = sid
                row["view_peer_user_id"] = rid
            else:
                row["view_user_id"] = rid
                row["view_peer_user_id"] = 0
            row["view_receiver_id"] = rid
        content = row.get("content") or ""
        if len(content) > 80:
            row["content_preview"] = content[:80] + "…"
        else:
            row["content_preview"] = content
        return row

    @staticmethod
    def admin_get_history(
        receiver_type,
        receiver_id,
        peer_user_id=0,
        limit=100,
        before_id=0,
    ):
        base = ImMessageRepository._sender_sql()
        if receiver_type == "group":
            sql = base + " WHERE m.receiver_type = 'group' AND m.receiver_id = ?"
            params = [receiver_id]
        elif peer_user_id:
            sql = base + """
                WHERE m.receiver_type = 'user' AND (
                    (m.sender_id = ? AND m.receiver_id = ?)
                    OR (m.sender_id = ? AND m.receiver_id = ?)
                )
            """
            params = [receiver_id, peer_user_id, peer_user_id, receiver_id]
        else:
            sql = base + """
                WHERE m.receiver_type = 'user' AND (
                    (m.sender_id = 0 AND m.receiver_id = ?)
                    OR (m.sender_id = ? AND m.employee_id > 0)
                )
            """
            params = [receiver_id, receiver_id]

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
