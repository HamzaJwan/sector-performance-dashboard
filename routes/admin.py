from flask import Blueprint, render_template, request, redirect, flash, url_for
import mysql.connector
from config import DB_CONFIG
import logger

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/', methods=['GET'])
def admin_panel():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT DISTINCT(branch) as name FROM sector_stats WHERE branch != 'Discovered hosts' ORDER BY name")
        branches = cursor.fetchall()

        cursor.execute("SELECT * FROM tower_staff ORDER BY full_name")
        staff = cursor.fetchall()

        cursor.execute("SELECT * FROM action_types ORDER BY name")
        action_types = cursor.fetchall()

        cursor.execute("SELECT * FROM evaluation_rules ORDER BY id")
        kpis = cursor.fetchall()

        return render_template('admin.html', branches=branches, tower_staff=staff, action_types=action_types, evaluation_rules=kpis)
    except Exception as e:
        logger.logging.error(f"admin_panel error: {e}")
        return "⚠️ فشل تحميل لوحة التحكم"
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/add_branch', methods=['POST'])
def add_branch():
    try:
        name = request.form['branch_name']
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO branches (name) VALUES (%s)", (name,))
        conn.commit()
        flash("✅ تم إضافة الفرع", "success")
    except Exception as e:
        logger.logging.error(f"add_branch error: {e}")
        flash("❌ فشل في إضافة الفرع", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/delete_branch', methods=['POST'])
def delete_branch():
    try:
        name = request.form['branch_name']
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM branches WHERE name = %s", (name,))
        conn.commit()
        flash("✅ تم حذف الفرع بنجاح", "success")
    except Exception as e:
        logger.logging.error(f"delete_branch error: {e}")
        flash("❌ فشل في حذف الفرع", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/add_action_type', methods=['POST'])
def add_action_type():
    try:
        name = request.form['name']
        description = request.form.get('description', '')
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO action_types (name, description) VALUES (%s, %s)", (name, description))
        conn.commit()
        flash("✅ تم إضافة نوع الإجراء", "success")
    except Exception as e:
        logger.logging.error(f"add_action_type error: {e}")
        flash("❌ فشل في إضافة نوع الإجراء", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/delete_action_type', methods=['POST'])
def delete_action_type():
    try:
        action_id = request.form['action_id']
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM action_types WHERE id = %s", (action_id,))
        conn.commit()
        flash("✅ تم حذف نوع الإجراء", "success")
    except Exception as e:
        logger.logging.error(f"delete_action_type error: {e}")
        flash("❌ فشل في حذف نوع الإجراء", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/add_staff', methods=['POST'])
def add_staff():
    try:
        full_name = request.form['full_name']
        username = request.form.get('username')
        phone = request.form.get('phone')
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tower_staff (full_name, username, phone) VALUES (%s, %s, %s)", (full_name, username, phone))
        conn.commit()
        flash("✅ تم إضافة الموظف", "success")
    except Exception as e:
        logger.logging.error(f"add_staff error: {e}")
        flash("❌ فشل في إضافة الموظف", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/delete_staff', methods=['POST'])
def delete_staff():
    try:
        staff_id = request.form['staff_id']
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tower_staff WHERE id = %s", (staff_id,))
        conn.commit()
        flash("✅ تم حذف الموظف", "success")
    except Exception as e:
        logger.logging.error(f"delete_staff error: {e}")
        flash("❌ فشل في حذف الموظف", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.admin_panel'))
