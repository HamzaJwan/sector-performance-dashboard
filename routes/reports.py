from flask import Blueprint, render_template, request
import mysql.connector
from config import DB_CONFIG
import logger

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')  # تمت إضافة url_prefix

@reports_bp.route('/')
def reports_home():
    return render_template('reports_home.html')

@reports_bp.route('/sector-history', methods=['GET', 'POST'])
def sector_history_selector():
    history = []
    if request.method == 'POST':
        hostname = request.form.get('hostname')
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM sector_stats WHERE hostname = %s ORDER BY last_updated DESC", (hostname,))
            history = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.logging.error(f"خطأ في تقرير تاريخ السكتور: {e}")
    return render_template('sector_history.html', history=history)

@reports_bp.route('/actions-summary')
def actions_summary():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT at.name AS action_type, COUNT(*) AS total_actions
            FROM sector_actions sa
            JOIN action_types at ON sa.action_type_id = at.id
            GROUP BY at.name
            ORDER BY total_actions DESC
        """)
        summary = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('actions_summary.html', summary=summary)
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير ملخص العمليات: {e}")
        return "خطأ في التقرير"

@reports_bp.route('/weekly')
def weekly():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT hostname, branch,
                   ROUND(AVG(avg_mbps), 2) AS avg_speed,
                   ROUND(MAX(max_mbps), 2) AS peak_speed,
                   ROUND(MAX(load_ratio), 2) AS max_load
            FROM sector_stats
            WHERE last_updated >= NOW() - INTERVAL 7 DAY
            GROUP BY hostname, branch
            ORDER BY max_load DESC
        """)
        stats = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('weekly_report.html', stats=stats)
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير الأداء الأسبوعي: {e}")
        return "خطأ في التقرير"
