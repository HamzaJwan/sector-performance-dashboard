import mysql.connector
from datetime import datetime, timedelta

# اتصال Zabbix
zabbix_conn = mysql.connector.connect(
    host='172.31.1.36',
    user='wnet',
    password='#Wnet2025',
    database='zabbix_db'
)

# اتصال بقاعدة بيانات الأداء
sectors_conn = mysql.connector.connect(
    host='localhost',
    port=3307,
    user='root',
    password='strongpass123',
    database='Sectors'
)

# إعداد فترة الذروة: من أمس 20:00 إلى اليوم 00:00
now = datetime.now()
today_midnight = datetime.combine(now.date(), datetime.min.time())
peak_start = today_midnight - timedelta(hours=4)
peak_end = today_midnight
peak_start_unix = int(peak_start.timestamp())
peak_end_unix = int(peak_end.timestamp())

print(f"📆 Peak window: {peak_start} → {peak_end}")

# 🔍 دالة للبحث عن itemid في عدة واجهات (حتى .10)
def get_itemid_flexible(hostid, key_base):
    cur = zabbix_conn.cursor()
    for i in range(1, 11):  # البحث من .1 إلى .10
        key_try = f"{key_base}.{i}]"
        cur.execute("SELECT itemid FROM items WHERE hostid = %s AND key_ = %s", (hostid, key_try))
        row = cur.fetchone()
        if row:
            return int(row[0])
    return None

# دالة لحساب المتوسط والأقصى من trends_uint
def get_peak_stats(itemid):
    cur = zabbix_conn.cursor()
    cur.execute("""
        SELECT AVG(value_avg), MAX(value_max)
        FROM trends_uint
        WHERE itemid = %s AND clock BETWEEN %s AND %s
    """, (itemid, peak_start_unix, peak_end_unix))
    avg_val, max_val = cur.fetchone()
    return float(avg_val or 0), float(max_val or 0)

# 🛰️ استخراج السكتورات الفعالة فقط من مجموعة Al Khomes
cursor = zabbix_conn.cursor(dictionary=True)
cursor.execute("""
    SELECT h.hostid, h.host, g.name AS groupname
    FROM hosts h
    JOIN hosts_groups hg ON h.hostid = hg.hostid
    JOIN hstgrp g ON hg.groupid = g.groupid
    WHERE g.name = 'Al Khomes'
      AND h.status = 0
      AND (h.host LIKE '%SEC%' OR h.host LIKE '%HORN%')
""")

sectors = cursor.fetchall()
print(f"🔍 Found {len(sectors)} active sectors in group 'Al Khomes'")

for sector in sectors:
    hostname = sector['host']
    hostid = sector['hostid']
    branch = sector['groupname']

    # 🔑 البحث عن itemid للزبائن والترافيك
    itemid_clients = get_itemid_flexible(hostid, 'ssid.regclient[mtxrWlApClientCount')
    itemid_traffic = get_itemid_flexible(hostid, 'net.if.out[ifHCOutOctets')

    if not itemid_clients or not itemid_traffic:
        print(f"⚠️ Skipping {hostname} (missing itemid)")
        continue

    # 📊 جمع الإحصائيات من Zabbix
    avg_traffic, max_traffic = get_peak_stats(itemid_traffic)
    _, max_clients = get_peak_stats(itemid_clients)

    avg_mbps = round(avg_traffic / 1_000_000, 2)
    max_mbps = round(max_traffic / 1_000_000, 2)
    load_ratio = round(avg_mbps / max_clients, 2) if max_clients else 0
    peak_load_ratio = round(max_mbps / max_clients, 2) if max_clients else 0

    # 💾 تخزين النتائج في قاعدة بيانات Sectors
    cur2 = sectors_conn.cursor()
    cur2.execute("""
        INSERT INTO sector_stats (
            hostname, itemid_clients, itemid_traffic,
            max_clients, avg_mbps, max_mbps,
            load_ratio, peak_load_ratio, branch, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        hostname, itemid_clients, itemid_traffic,
        max_clients, avg_mbps, max_mbps,
        load_ratio, peak_load_ratio, branch, peak_end
    ))
    sectors_conn.commit()
    print(f"✅ {hostname}: max_clients={max_clients}, avg_mbps={avg_mbps}, max_mbps={max_mbps}")

# 🧹 إغلاق الاتصالات
cursor.close()
zabbix_conn.close()
sectors_conn.close()
