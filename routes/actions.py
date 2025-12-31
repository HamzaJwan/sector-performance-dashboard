from flask import Blueprint, render_template, request, redirect, url_for, flash
import mysql.connector
from config import DB_CONFIG
import logger

actions_bp = Blueprint('actions', __name__)

@actions_bp.route('/actions', methods=['GET', 'POST'])
def actions():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            hostname = request.form['hostname']
            action_type = request.form['action_type']
            performed_by = request.form['performed_by']
            notes = request.form['notes']

            cursor.execute("""
                INSERT INTO sector_actions (hostname, action_type_id, performed_by, notes)
                VALUES (%s, %s, %s, %s)
            """, (hostname, action_type, performed_by, notes))
            conn.commit()
            flash("✅ تم تسجيل العملية بنجاح", "success")
            return redirect(url_for('actions.actions'))

        # جلب الأنواع
        cursor.execute("SELECT * FROM action_types")
        action_types = cursor.fetchall()

        # جلب الإجراءات المسجلة
        cursor.execute("""
            SELECT sa.*, at.name AS action_name
            FROM sector_actions sa
            JOIN action_types at ON sa.action_type_id = at.id
            ORDER BY sa.performed_at DESC
        """)
        actions = cursor.fetchall()

        # جلب الفروع
        cursor.execute("SELECT * FROM branches")
        branches = cursor.fetchall()

        # جلب السكتورات المرتبطة بفروع
        cursor.execute("SELECT DISTINCT hostname, branch FROM sector_stats")
        sectors = cursor.fetchall()

        # جلب الموظفين (بدون branch)
        cursor.execute("SELECT id, full_name FROM tower_staff")
        staff = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            'actions.html',
            actions=actions,
            action_types=action_types,
            branches=branches,
            sectors=sectors,
            staff=staff
        )
    except Exception as e:
        logger.logging.error(f"خطأ في صفحة الإجراءات: {e}")
        return "حدث خطأ يرجى المحاولة لاحقًا"
