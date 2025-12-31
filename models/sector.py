import mysql.connector
from config import DB_CONFIG
import logger

def fetch_sectors(start_date=None, end_date=None, evaluation=None, branch=None):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM sector_stats WHERE 1=1"
        params = []

        if start_date:
            query += " AND last_updated >= %s"
            params.append(start_date)

        if end_date:
            query += " AND last_updated <= %s"
            params.append(end_date)

        if evaluation:
            query += " AND evaluation = %s"
            params.append(evaluation)

        if branch:
            query += " AND branch = %s"
            params.append(branch)

        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.logging.error(f"Database fetch error: {e}")
        return []

def fetch_weekly_report():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = '''
            SELECT branch, hostname, AVG(avg_mbps) AS avg_speed,
                   MAX(max_mbps) AS peak_speed,
                   MAX(load_ratio) AS max_load
            FROM sector_stats
            WHERE last_updated >= NOW() - INTERVAL 7 DAY
            GROUP BY branch, hostname
            ORDER BY max_load DESC
        '''
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.logging.error(f"Report fetch error: {e}")
        return []
