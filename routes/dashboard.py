from flask import Blueprint, render_template, request
from config import db_connection
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def dashboard():
    branch_filter = request.args.get('branch')
    eval_filter = request.args.get('evaluation')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # التاريخ الحالي كافتراضي
    today = datetime.today().strftime('%Y-%m-%d')
    start = start_date if start_date else today
    end = end_date if end_date else today

    with db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT hostname AS hostname,
                   branch AS branch,
                   ip, frequency, firmware_version, uptime,
                   max_clients, avg_mbps, max_mbps,
                   evaluation, timestamp
            FROM sector_stats
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """
        params = [start, end]

        if branch_filter:
            query += " AND branch = %s"
            params.append(branch_filter)

        if eval_filter:
            query += " AND evaluation = %s"
            params.append(eval_filter)

        query += " ORDER BY max_clients DESC"

        cursor.execute(query, params)
        stats = cursor.fetchall()

    # استخراج القيم المتاحة للتصفية
    branches = sorted(list(set(s['branch'] for s in stats if s.get('branch'))))
    evaluations = sorted(list(set(s['evaluation'] for s in stats if s.get('evaluation'))))

    return render_template(
        'dashboard.html',
        stats=stats,
        branches=branches,
        evaluations=evaluations,
        selected_branch=branch_filter,
        selected_eval=eval_filter,
        start_date=start,
        end_date=end
    )
