from app.models.db import get_connection


# 群状态：1=正常  0=封禁（可解封）  2=解散（不可恢复）
GROUP_STATUS_ACTIVE = 1
GROUP_STATUS_BANNED = 0
GROUP_STATUS_DISSOLVED = 2


class ImGroupRepository:
    @staticmethod
    def create(name, owner_id, member_ids=None, employee_ids=None):
        member_ids = list(set(member_ids or []))
        employee_ids = list(set(employee_ids or []))
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
            for eid in employee_ids:
                conn.execute(
                    "INSERT INTO im_group_employees(group_id, employee_id) VALUES(?, ?)",
                    (group_id, eid),
                )
            conn.commit()
        return group_id

    @staticmethod
    def get_status(group_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT status FROM im_groups WHERE id = ?",
                (group_id,),
            ).fetchone()
            return row["status"] if row else None

    @staticmethod
    def is_active(group_id):
        return ImGroupRepository.get_status(group_id) == GROUP_STATUS_ACTIVE

    @staticmethod
    def get_block_message(group_id):
        status = ImGroupRepository.get_status(group_id)
        if status == GROUP_STATUS_BANNED:
            return "该群已被管理员封禁，无法发送消息"
        if status == GROUP_STATUS_DISSOLVED:
            return "该群已被管理员解散，无法继续聊天"
        return None

    @staticmethod
    def add_employees(group_id, operator_id, employee_ids):
        group = ImGroupRepository.get_by_id_admin(group_id)
        if not group:
            return False, "群组不存在"
        block = ImGroupRepository.get_block_message(group_id)
        if block:
            return False, block
        if not ImGroupRepository.is_member(group_id, operator_id):
            return False, "无权限"
        with get_connection() as conn:
            for eid in employee_ids:
                exists = conn.execute(
                    "SELECT id FROM im_group_employees WHERE group_id = ? AND employee_id = ?",
                    (group_id, eid),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO im_group_employees(group_id, employee_id) VALUES(?, ?)",
                        (group_id, eid),
                    )
            conn.commit()
        return True, "数字员工已加入群聊"

    @staticmethod
    def get_employees(group_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT ge.employee_id, de.name, de.alias, de.icon, de.description
                FROM im_group_employees ge
                JOIN digital_employees de ON de.id = ge.employee_id
                WHERE ge.group_id = ? AND de.status = 1
                ORDER BY de.sort_order ASC
                """,
                (group_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_group_detail(group_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM im_groups WHERE id = ? AND status = 1",
                (group_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_id(group_id):
        return ImGroupRepository.get_group_detail(group_id)

    @staticmethod
    def get_user_groups(user_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT g.id, g.name, g.owner_id, g.announcement, g.create_at, g.status,
                       m.role AS my_role
                FROM im_groups g
                JOIN im_group_members m ON m.group_id = g.id
                WHERE m.user_id = ?
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
        group = ImGroupRepository.get_by_id_admin(group_id)
        if not group:
            return False, "群组不存在"
        block = ImGroupRepository.get_block_message(group_id)
        if block:
            return False, block
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

    @staticmethod
    def get_all(page=1, page_size=20, keyword=None):
        offset = (page - 1) * page_size
        query = """
            SELECT g.*, u.username AS owner_name,
                   (SELECT COUNT(*) FROM im_group_members m WHERE m.group_id = g.id) AS member_count
            FROM im_groups g
            LEFT JOIN users u ON u.id = g.owner_id
        """
        count_query = "SELECT COUNT(*) FROM im_groups g"
        params = []
        count_params = []
        if keyword:
            where = " WHERE g.name LIKE ?"
            query += where
            count_query += where
            params.append(f"%{keyword}%")
            count_params.append(f"%{keyword}%")
        query += " ORDER BY g.id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            total = conn.execute(count_query, count_params).fetchone()[0]
            return [dict(r) for r in rows], total

    @staticmethod
    def dissolve(group_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT status FROM im_groups WHERE id = ?",
                (group_id,),
            ).fetchone()
            if not row:
                return False, "群组不存在"
            if row["status"] == GROUP_STATUS_DISSOLVED:
                return False, "群已解散"
            conn.execute(
                "UPDATE im_groups SET status = ? WHERE id = ?",
                (GROUP_STATUS_DISSOLVED, group_id),
            )
            conn.commit()
        return True, "群已解散"

    @staticmethod
    def set_status(group_id, status):
        """封禁/解封：仅支持 0↔1，已解散群不可变更"""
        if status not in (GROUP_STATUS_ACTIVE, GROUP_STATUS_BANNED):
            return False, "无效状态"
        with get_connection() as conn:
            row = conn.execute(
                "SELECT status FROM im_groups WHERE id = ?",
                (group_id,),
            ).fetchone()
            if not row:
                return False, "群组不存在"
            current = row["status"]
            if current == GROUP_STATUS_DISSOLVED:
                return False, "该群已解散，无法解封或封禁"
            if status == GROUP_STATUS_ACTIVE and current == GROUP_STATUS_ACTIVE:
                return False, "群已是正常状态"
            if status == GROUP_STATUS_BANNED and current == GROUP_STATUS_BANNED:
                return False, "群已是封禁状态"
            conn.execute(
                "UPDATE im_groups SET status = ? WHERE id = ?",
                (status, group_id),
            )
            conn.commit()
        if status == GROUP_STATUS_BANNED:
            return True, "群已封禁"
        return True, "群已解封"

    @staticmethod
    def set_announcement(group_id, announcement):
        with get_connection() as conn:
            conn.execute(
                "UPDATE im_groups SET announcement = ? WHERE id = ?",
                (announcement, group_id),
            )
            conn.commit()

    @staticmethod
    def get_by_id_admin(group_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM im_groups WHERE id = ?",
                (group_id,),
            ).fetchone()
            return dict(row) if row else None
