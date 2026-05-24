from app.models.db import get_connection


class ImGroupRepository:
    @staticmethod
    def create(name, owner_id, member_ids=None):
        member_ids = list(set(member_ids or []))
        if owner_id not in member_ids:
            member_ids.append(owner_id)
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO im_groups(name, owner_id, status) VALUES(?, ?, 1)",
                (name, owner_id),
            )
            group_id = cur.lastrowid
            for uid in member_ids:
                role = "owner" if uid == owner_id else "member"
                conn.execute(
                    "INSERT INTO im_group_members(group_id, user_id, role) VALUES(?, ?, ?)",
                    (group_id, uid, role),
                )
            conn.commit()
        return group_id

    @staticmethod
    def get_by_id(group_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM im_groups WHERE id = ? AND status = 1",
                (group_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_user_groups(user_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT g.id, g.name, g.owner_id, g.announcement, g.create_at,
                       m.role AS my_role
                FROM im_groups g
                JOIN im_group_members m ON m.group_id = g.id
                WHERE m.user_id = ? AND g.status = 1
                ORDER BY g.id DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def join_group(group_id, user_id):
        with get_connection() as conn:
            group = conn.execute(
                "SELECT id FROM im_groups WHERE id = ? AND status = 1",
                (group_id,),
            ).fetchone()
            if not group:
                return False, "群组不存在"
            exists = conn.execute(
                "SELECT id FROM im_group_members WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            ).fetchone()
            if exists:
                return False, "已在群中"
            conn.execute(
                "INSERT INTO im_group_members(group_id, user_id, role) VALUES(?, ?, 'member')",
                (group_id, user_id),
            )
            conn.commit()
        return True, "加入成功"

    @staticmethod
    def add_members(group_id, operator_id, member_ids):
        group = ImGroupRepository.get_by_id(group_id)
        if not group:
            return False, "群组不存在"
        if not ImGroupRepository.is_member(group_id, operator_id):
            return False, "无权限"
        with get_connection() as conn:
            for uid in member_ids:
                exists = conn.execute(
                    "SELECT id FROM im_group_members WHERE group_id = ? AND user_id = ?",
                    (group_id, uid),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO im_group_members(group_id, user_id, role) VALUES(?, ?, 'member')",
                        (group_id, uid),
                    )
            conn.commit()
        return True, "成员已添加"

    @staticmethod
    def is_member(group_id, user_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM im_group_members WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            ).fetchone()
            return row is not None

    @staticmethod
    def get_members(group_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.user_id, m.role, u.username
                FROM im_group_members m
                JOIN users u ON u.id = m.user_id
                WHERE m.group_id = ?
                ORDER BY m.role DESC, u.username
                """,
                (group_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_member_ids(group_id):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT user_id FROM im_group_members WHERE group_id = ?",
                (group_id,),
            ).fetchall()
            return [r["user_id"] for r in rows]
