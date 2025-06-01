from flask import Flask, render_template, request
import mysql.connector
from datetime import datetime

app = Flask(__name__)

def get_sector_data(branch=None, start_date=None, end_date=None):
    conn = mysql.connector.connect(
        host="localhost",
        port=3307,
        user="root",
        password="strongpass123",
        database="Sectors"
    )
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT s1.*
        FROM sector_stats s1
        JOIN (
            SELECT hostname, MAX(last_updated) AS max_time
            FROM sector_stats
            WHERE DATE(last_updated) BETWEEN %s AND %s
            GROUP BY hostname
        ) s2 ON s1.hostname = s2.hostname AND s1.last_updated = s2.max_time
    """

    params = [start_date, end_date]

    if branch:
        query += " WHERE s1.branch = %s ORDER BY s1.branch, s1.hostname"
        params.append(branch)
    else:
        query += " ORDER BY s1.branch, s1.hostname"

    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    return data

def classify_sector(sector):
    statuses = []

    if sector["max_clients"] is None or sector["avg_mbps"] is None:
        statuses.append(("بلا بيانات", "gray", "نرجو مراجعة الجهاز والزابكس"))
        return statuses

    if sector["max_clients"] <= 5:
        statuses.append(("يحتاج دعم", "blue", "عدد الزبائن قليل جدًا. نرجو إضافة زبائن لهذا السكتور."))

    if sector["max_clients"] > 25 and sector["avg_mbps"] < 15:
        statuses.append(("ازدحام", "orange", "عدد الزبائن مرتفع والسرعة منخفضة. نرجو التخفيف على السكتور."))

    if sector["avg_mbps"] < 5:
        statuses.append(("ضعيف جدًا", "red", "السرعة ضعيفة جدًا. نرجو تغيير التردد أو تحليل السبب."))

    if 5 <= sector["avg_mbps"] < 10:
        statuses.append(("متذبذب", "yellow", "السرعة متوسطة لكنها غير مستقرة (5-10 Mbps)."))

    if not statuses:
        statuses.append(("جيد", "green", "عدد الزبائن مناسب والأداء جيد."))

    return statuses

@app.route("/")
def dashboard():
    branch = request.args.get("branch")
    selected_status = request.args.get("status")
    start_date = request.args.get("start_date") or datetime.today().strftime("%Y-%m-%d")
    end_date = request.args.get("end_date") or datetime.today().strftime("%Y-%m-%d")

    sectors = get_sector_data(branch, start_date, end_date)
    branches = sorted(list(set([s["branch"] for s in sectors])))

    for s in sectors:
        s["statuses"] = classify_sector(s)

    return render_template("dashboard.html",
        sectors=sectors,
        branches=branches,
        selected_branch=branch,
        selected_status=selected_status,
        start_date=start_date,
        end_date=end_date
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
