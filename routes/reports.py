from flask import Blueprint, render_template, request
import mysql.connector
from config import DB_CONFIG
import logger

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
def reports_home():
    return render_template('reports_home.html')

# ✅ 1. تقرير أسوأ 10 سكتورات يوميًا
@reports_bp.route('/worst-daily', methods=['GET', 'POST'])
def worst_daily():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # جلب الفروع المتاحة
        cursor.execute("SELECT DISTINCT branch FROM sector_stats ORDER BY branch")
        branches = [row['branch'] for row in cursor.fetchall()]

        # قراءة الفرع المحدد من الطلب
        selected_branch = request.form.get('branch')

        # تعديل الاستعلام حسب الفرع
        if selected_branch:
            cursor.execute("""
                SELECT * FROM sector_stats
                WHERE last_updated >= CURDATE() AND branch = %s
                ORDER BY load_ratio DESC
                LIMIT 10
            """, (selected_branch,))
        else:
            cursor.execute("""
                SELECT * FROM sector_stats
                WHERE last_updated >= CURDATE()
                ORDER BY load_ratio DESC
                LIMIT 10
            """)

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template("report_template.html",
            title="📉 تقرير: أسوأ 10 سكتورات يوميًا",
            icon="📉",
            description="يعرض السكتورات الأسوء من حيث التحميل خلال اليوم الحالي.",
            purpose="تحديد أكثر السكتورات اختناقًا لاتخاذ إجراء عاجل.",
            table_headers=["السكتور", "الفرع", "🛋 السرعة", "🔥 التحميل", "📊 التقييم"],
            table_data=[{
                "السكتور": row["hostname"],
                "الفرع": row["branch"],
                "🛋 السرعة": row["avg_mbps"],
                "🔥 التحميل": row["load_ratio"],
                "📊 التقييم": row["evaluation"]
            } for row in data],
            branches=branches,
            selected_branch=selected_branch
        )
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير أسوأ السكتورات: {e}")
        return render_template("error.html", message="حدث خطأ في تقرير أسوأ السكتورات.")
# ✅ 2. تقرير الأداء اليومي
@reports_bp.route('/performance-drop', methods=['GET', 'POST'])
def performance_drop():
    selected_branch = request.form.get("branch") or ""
    selected_days = int(request.form.get("days") or 3)
    drop_percentage = float(request.form.get("drop") or 40)
    branches = []

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # جلب الفروع
        cursor.execute("SELECT DISTINCT branch FROM sector_stats ORDER BY branch")
        branches = [row["branch"] for row in cursor.fetchall()]

        # آخر تاريخ متاح في البيانات
        cursor.execute("SELECT MAX(stat_date) AS latest FROM sector_stats")
        latest_date = cursor.fetchone()["latest"]

        # الاستعلام مع تطبيق شرط النسبة المدخلة
        query = f"""
            SELECT s1.hostname, s1.branch, s1.avg_mbps AS today_speed,
                   ROUND(s2.avg_week, 2) AS weekly_avg,
                   s1.evaluation
            FROM sector_stats s1
            JOIN (
                SELECT hostname, AVG(avg_mbps) AS avg_week
                FROM sector_stats
                WHERE stat_date BETWEEN %s - INTERVAL %s DAY AND %s - INTERVAL 1 DAY
                GROUP BY hostname
            ) s2 ON s1.hostname = s2.hostname
            WHERE s1.stat_date = %s AND s1.avg_mbps < (s2.avg_week * %s)
        """

        percentage_factor = (100 - drop_percentage) / 100
        params = (latest_date, selected_days, latest_date, latest_date, percentage_factor)

        if selected_branch:
            query += " AND s1.branch = %s"
            params += (selected_branch,)

        query += " ORDER BY (s2.avg_week - s1.avg_mbps) DESC"

        cursor.execute(query, params)
        data = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("report_template.html",
            title="🔻 تقرير: انخفاض الأداء",
            icon="🔻",
            description=f"تحليل السكتورات التي سجلت اليوم أداءً أقل من المعتاد بـ {int(drop_percentage)}% خلال الأيام الماضية.",
            purpose="تحديد السكتورات التي شهدت تراجعًا ملحوظًا في الأداء لاتخاذ إجراءات تصحيحية مبكرة.",
            branches=branches,
            selected_branch=selected_branch,
            selected_days=selected_days,
            selected_drop=drop_percentage,
            table_headers=["السكتور", "الفرع", "🚀 معدل اليوم", "📊 متوسط الفترة", "📊 التقييم"],
            table_data=[{
                "السكتور": row["hostname"],
                "الفرع": row["branch"],
                "🚀 معدل اليوم": row["today_speed"],
                "📊 متوسط الفترة": row["weekly_avg"],
                "📊 التقييم": row["evaluation"]
            } for row in data]
        )
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير انخفاض الأداء: {e}")
        return render_template("error.html", message="حدث خطأ في تقرير انخفاض الأداء.")

# 4. تقرير تطور أداء سكتور معين
@reports_bp.route('/evolution', methods=['GET', 'POST'])
def sector_evolution():
    branches = []
    hostnames = []
    history = []
    selected_branch = request.form.get('branch')
    selected_hostname = request.form.get('hostname')
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT branch FROM sector_stats ORDER BY branch")
        branches = [row['branch'] for row in cursor.fetchall()]

        if selected_branch:
            cursor.execute("SELECT DISTINCT hostname FROM sector_stats WHERE branch = %s", (selected_branch,))
            hostnames = [row['hostname'] for row in cursor.fetchall()]

        if selected_hostname:
            cursor.execute("""
                SELECT last_updated, avg_mbps, max_mbps, load_ratio, evaluation
                FROM sector_stats
                WHERE hostname = %s
                ORDER BY last_updated ASC
            """, (selected_hostname,))
            history = cursor.fetchall()

        cursor.close()
        conn.close()
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير تطور السكتور: {e}")

    return render_template("report_template.html",
        title="📈 تقرير: تطور أداء سكتور معين",
        icon="📈",
        description="رصد الأداء الزمني لسكتور محدد بناءً على بيانات حقيقية.",
        purpose="تحليل تحسن أو تدهور أداء السكتور بعد الصيانة أو التعديلات.",
        table_headers=["📅 التاريخ", "🛋 متوسط السرعة", "🚀 السرعة القصوى", "🔥 الحمل", "📊 التقييم"],
        table_data=[{
            "📅 التاريخ": row["last_updated"],
            "🛋 متوسط السرعة": row["avg_mbps"],
            "🚀 السرعة القصوى": row["max_mbps"],
            "🔥 الحمل": row["load_ratio"],
            "📊 التقييم": row["evaluation"]
        } for row in history],
        branches=branches,
        selected_branch=selected_branch,
        hostnames=hostnames,
        selected_hostname=selected_hostname
    )
# 5. تقرير التقييم حسب الفروع
@reports_bp.route('/evaluation-summary')
def evaluation_summary():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT branch, evaluation, COUNT(*) AS count
            FROM sector_stats
            WHERE last_updated >= CURDATE()
            GROUP BY branch, evaluation
        """)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("report_template.html",
            title="🏷️ تقرير: التقييم حسب الفروع",
            icon="🏷️",
            description="عدد السكتورات المصنفة حسب التقييم في كل فرع.",
            purpose="معرفة الفروع التي تحتاج إلى دعم فني أو تحسين البنية التحتية.",
            table_headers=["الفرع", "📊 التقييم", "📦 العدد"],
            table_data=[{
                "الفرع": row["branch"],
                "📊 التقييم": row["evaluation"],
                "📦 العدد": row["count"]
            } for row in data]
        )
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير التقييم: {e}")
        return render_template("error.html", message="حدث خطأ في تقرير التقييم.")

# 6. تقرير الأداء الأسبوعي (مع فلترة حسب الفرع)
@reports_bp.route('/weekly', methods=['GET', 'POST'])
def weekly():
    selected_branch = request.form.get('branch') or None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # جميع الفروع المتاحة
        cursor.execute("SELECT DISTINCT branch FROM sector_stats ORDER BY branch")
        branches = [row['branch'] for row in cursor.fetchall()]

        # SQL حسب الفرع
        if selected_branch:
            cursor.execute("""
                SELECT hostname, branch,
                       ROUND(AVG(avg_mbps), 2) AS avg_speed,
                       ROUND(MAX(max_mbps), 2) AS peak_speed,
                       ROUND(MAX(load_ratio), 2) AS max_load
                FROM sector_stats
                WHERE last_updated >= NOW() - INTERVAL 7 DAY
                  AND branch = %s
                GROUP BY hostname, branch
                ORDER BY max_load DESC
            """, (selected_branch,))
        else:
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

        return render_template("report_template.html",
            title="📊 تقرير: الأداء الأسبوعي",
            icon="📊",
            description="يعرض هذا التقرير الأداء التفصيلي لكل سكتور خلال الأيام السبعة الماضية من حيث متوسط السرعة، السرعة القصوى، وأعلى حمل تم تسجيله.",
            purpose="مراقبة التغيرات الأسبوعية واتخاذ قرارات مبنية على البيانات.",
            table_headers=["الفرع", "السكتور", "📶 متوسط السرعة", "🚀 السرعة القصوى", "🔥 أعلى حمل"],
            table_data=[{
                "الفرع": row["branch"],
                "السكتور": row["hostname"],
                "📶 متوسط السرعة": row["avg_speed"],
                "🚀 السرعة القصوى": row["peak_speed"],
                "🔥 أعلى حمل": row["max_load"]
            } for row in stats],
            branches=branches,
            selected_branch=selected_branch
        )
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير الأداء الأسبوعي: {e}")
        return render_template("error.html", message="حدث خطأ في تقرير الأداء الأسبوعي.")

# 7. ملخص عمليات الصيانة
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
        return render_template("report_template.html",
            title="🛠️ تقرير: ملخص عمليات الصيانة",
            icon="🛠️",
            description="إحصائية بعدد كل نوع من أنواع الصيانة المنفذة.",
            purpose="تحليل نشاط الصيانة وتحسين جدولة المهام.",
            table_headers=["نوع العملية", "📦 العدد"],
            table_data=[{
                "نوع العملية": row["action_type"],
                "📦 العدد": row["total_actions"]
            } for row in summary]
        )
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير ملخص العمليات: {e}")
        return render_template("error.html", message="حدث خطأ في تقرير ملخص الصيانة.")

# ✅ 8. تقرير تاريخ تقييم السكتور (بدون رسم)
@reports_bp.route('/evaluation-history', methods=['GET', 'POST'])
def evaluation_history():
    branches = []
    hostnames = []
    evaluations = []
    table_data = []
    selected_branch = request.form.get('branch')
    selected_hostname = request.form.get('hostname')
    selected_period = request.form.get('period') or '7'
    period_days = int(selected_period)

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # جلب الفروع
        cursor.execute("SELECT DISTINCT branch FROM sector_stats ORDER BY branch")
        branches = [row['branch'] for row in cursor.fetchall()]

        # جلب السكتورات حسب الفرع
        if selected_branch:
            cursor.execute("SELECT DISTINCT hostname FROM sector_stats WHERE branch = %s", (selected_branch,))
            hostnames = [row['hostname'] for row in cursor.fetchall()]

        # جلب التقييمات
        if selected_hostname:
            cursor.execute("""
                SELECT stat_date, avg_mbps, max_mbps, load_ratio, evaluation
                FROM sector_stats
                WHERE hostname = %s AND stat_date >= CURDATE() - INTERVAL %s DAY
                ORDER BY stat_date ASC
            """, (selected_hostname, period_days))
            evaluations = cursor.fetchall()

        # تحضير البيانات للجدول
        for row in evaluations:
            table_data.append({
                "📅 التاريخ": row["stat_date"].strftime('%Y-%m-%d'),
                "📶 متوسط السرعة": row["avg_mbps"],
                "🚀 السرعة القصوى": row["max_mbps"],
                "🔥 التحميل": row["load_ratio"],
                "📊 التقييم": row["evaluation"]
            })

        # تحليل التقييمات
        eval_counts = {}
        for row in evaluations:
            val = row['evaluation']
            eval_counts[val] = eval_counts.get(val, 0) + 1

        if len(eval_counts) == 1:
            summary = f"الأداء مستقر ({list(eval_counts.keys())[0]}) ✅"
        elif "ازدحام" in eval_counts or "يحتاج دعم" in eval_counts:
            summary = "⚠️ السكتور شهد تذبذبًا ملحوظًا خلال الفترة."
        elif len(eval_counts) >= 3:
            summary = "📊 السكتور يتنقل بين تقييمات مختلفة مما يستدعي المتابعة."
        else:
            summary = "🟡 السكتور غير مستقر، ويوصى بالمراقبة المستمرة."

        cursor.close()
        conn.close()

        return render_template("report_template.html",
            title="📊 تقرير: تاريخ تقييم السكتور",
            icon="📊",
            description="عرض تاريخي لتغير تقييم السكتور (ممتاز، جيد، ازدحام...) بشكل تحليلي مفصل.",
            purpose="تحليل استقرار أو تدهور السكتور بناءً على تقييماته الزمنية.",
            table_headers=["📅 التاريخ", "📶 متوسط السرعة", "🚀 السرعة القصوى", "🔥 التحميل", "📊 التقييم"],
            table_data=table_data,
            branches=branches,
            hostnames=hostnames,
            selected_branch=selected_branch,
            selected_hostname=selected_hostname,
            selected_period=selected_period,
            summary=summary
        )
    except Exception as e:
        logger.logging.error(f"خطأ في تقرير تاريخ التقييم: {e}")
        return render_template("error.html", message="حدث خطأ في التقرير.")
