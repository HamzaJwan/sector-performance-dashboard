<<<<<<< HEAD
import mysql.connector
from datetime import datetime, timedelta

# اتصال Zabbix
=======

import mysql.connector
from datetime import datetime, timedelta
import pytz

>>>>>>> 84d317f ( النسخة الثانية:)
zabbix_conn = mysql.connector.connect(
    host='172.31.1.36',
    user='wnet',
    password='#Wnet2025',
    database='zabbix_db'
)

<<<<<<< HEAD
# اتصال بقاعدة بيانات الأداء
=======
>>>>>>> 84d317f ( النسخة الثانية:)
sectors_conn = mysql.connector.connect(
    host='localhost',
    port=3307,
    user='root',
    password='strongpass123',
    database='Sectors'
)

<<<<<<< HEAD
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
=======
tz = pytz.timezone("Africa/Tripoli")
now = datetime.now(tz)
today_midnight = datetime.combine(now.date(), datetime.min.time()).astimezone(tz)
peak_start = today_midnight - timedelta(hours=4)
peak_end = today_midnight
today_str = now.strftime("%Y-%m-%d")
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
print(f"📆 Peak window: {peak_start} → {peak_end}")

zbx_cur = zabbix_conn.cursor(dictionary=True)
zbx_cur.execute(f"""
    SELECT 
        h.host AS hostname,
        h.hostid,
        g.name AS branch,
        ROUND(tt.avg_val / 1000000, 2) AS avg_mbps,
        ROUND(tt.max_val / 1000000, 2) AS max_mbps,
        tc.max_val AS max_clients,
        ROUND((tt.avg_val / 1000000) / NULLIF(tc.max_val, 0), 2) AS load_ratio,
        ROUND((tt.max_val / 1000000) / NULLIF(tc.max_val, 0), 2) AS peak_load_ratio
    FROM 
        hosts h
    JOIN hosts_groups hg ON h.hostid = hg.hostid
    JOIN hstgrp g ON hg.groupid = g.groupid
    JOIN (
        SELECT hostid, avg_val, max_val
        FROM (
            SELECT 
                i.hostid,
                t.avg_val,
                t.max_val,
                ROW_NUMBER() OVER (PARTITION BY i.hostid ORDER BY
                    CASE
                        WHEN i.name = 'Interface wlan1(): Bits sent' THEN 1
                        WHEN i.name LIKE '%wlan1%' THEN 2
                        WHEN i.name LIKE '%bridge1%' THEN 3
                        ELSE 4
                    END
                ) AS rn
            FROM items i
            JOIN (
                SELECT itemid, AVG(value_avg) AS avg_val, MAX(value_max) AS max_val
                FROM trends_uint
                WHERE clock BETWEEN UNIX_TIMESTAMP('{peak_start.strftime("%Y-%m-%d %H:%M:%S")}')
                                AND UNIX_TIMESTAMP('{peak_end.strftime("%Y-%m-%d %H:%M:%S")}')
                GROUP BY itemid
            ) t ON t.itemid = i.itemid
            WHERE i.key_ LIKE 'net.if.out[ifHCOutOctets.%'
        ) ranked
        WHERE rn = 1
    ) tt ON tt.hostid = h.hostid
    JOIN (
        SELECT hostid, max_val
        FROM (
            SELECT 
                i.hostid,
                t.max_val,
                ROW_NUMBER() OVER (PARTITION BY i.hostid ORDER BY
                    CASE
                        WHEN i.name LIKE '%AP registered clients%' THEN 1
                        WHEN i.name LIKE '%client%' THEN 2
                        ELSE 3
                    END
                ) AS rn
            FROM items i
            JOIN (
                SELECT itemid, MAX(value_max) AS max_val
                FROM trends_uint
                WHERE clock BETWEEN UNIX_TIMESTAMP('{peak_start.strftime("%Y-%m-%d %H:%M:%S")}')
                                AND UNIX_TIMESTAMP('{peak_end.strftime("%Y-%m-%d %H:%M:%S")}')
                GROUP BY itemid
            ) t ON t.itemid = i.itemid
            WHERE i.key_ LIKE 'ssid.regclient[mtxrWlApClientCount.%'
        ) ranked
        WHERE rn = 1
    ) tc ON tc.hostid = h.hostid
    WHERE 
        h.status = 0
        AND (h.host LIKE '%SEC%' OR h.host LIKE '%HORN%')
    ORDER BY g.name, h.host
""")

results = zbx_cur.fetchall()
print(f"📡 Found {len(results)} sectors")

def evaluate_sector(avg_mbps, max_clients):
    statuses = []

    # فقط في حالة لا توجد بيانات إطلاقًا
    if (avg_mbps is None or avg_mbps == 0) and (max_clients is None or max_clients == 0):
        return "⚫ بلا بيانات"

    if avg_mbps < 5:
        statuses.append("🔴 ضعيف جدًا")

    if max_clients > 25:
        statuses.append("🟠 ازدحام")

    if max_clients <= 5:
        statuses.append("🔵 يحتاج دعم")

    if 5 <= avg_mbps <= 10:
        statuses.append("🟡 متذبذب")

    if 5 <= max_clients <= 25 and avg_mbps > 15:
        statuses.append("🟢 جيد")

    return ", ".join(statuses) if statuses else "🟠 غير مصنف"
    if not frequency or frequency.strip() == "":
        return "⚫ بلا بيانات"

    statuses = []
    if 5 <= max_clients <= 25 and avg_mbps > 15:
        statuses.append("🟢 جيد")
    if avg_mbps < 5:
        statuses.append("🔴 ضعيف جدًا")
    if max_clients > 25 and avg_mbps < 15:
        statuses.append("🟠 ازدحام")
    if max_clients <= 5:
        statuses.append("🔵 يحتاج دعم")
    if 5 <= avg_mbps <= 10:
        statuses.append("🟡 متذبذب")
    if avg_mbps > 10 and 5 < max_clients < 30 and not statuses:
        statuses.append("🟢 جيد")
    return ", ".join(statuses) if statuses else "⚫ بلا بيانات"

def get_ip_address(hostid):
    cur = zabbix_conn.cursor()
    cur.execute("SELECT ip FROM interface WHERE hostid = %s LIMIT 1", (hostid,))
    row = cur.fetchone()
    return row[0] if row else ""

def get_string_value(hostid, key):
    cur = zabbix_conn.cursor()
    cur.execute("""
        SELECT hi.value
        FROM items i
        JOIN history_str hi ON hi.itemid = i.itemid
        WHERE i.hostid = %s AND i.key_ = %s
        ORDER BY hi.clock DESC
        LIMIT 1
    """, (hostid, key))
    row = cur.fetchone()
    return row[0] if row else ""

def get_uint_value(hostid, key):
    cur = zabbix_conn.cursor()
    cur.execute("""
        SELECT hu.value
        FROM items i
        JOIN history_uint hu ON hu.itemid = i.itemid
        WHERE i.hostid = %s AND i.key_ = %s
        ORDER BY hu.clock DESC
        LIMIT 1
    """, (hostid, key))
    row = cur.fetchone()
    return row[0] if row else 0

for row in results:
    hostname = row['hostname']
    hostid = row['hostid']
    branch = row['branch']
    avg_mbps = row['avg_mbps']
    max_mbps = row['max_mbps']
    max_clients = row['max_clients']
    load_ratio = row['load_ratio']
    peak_load_ratio = row['peak_load_ratio']
    ip = get_ip_address(hostid)
    band_raw = get_string_value(hostid, 'ssid.band[mtxrWlApBand.1]')
    frequency = band_raw.split("/")[0] if "/" in band_raw else band_raw
    firmware = get_string_value(hostid, 'system.hw.firmware')
    uptime = get_uint_value(hostid, 'system.uptime[sysUpTime.0]')
    evaluation = evaluate_sector(avg_mbps, max_clients)

    cur2 = sectors_conn.cursor()
    cur2.execute("""
        INSERT INTO sector_stats (
            hostname, max_clients, avg_mbps, max_mbps, load_ratio, peak_load_ratio,
            branch, last_updated, ip, frequency, firmware_version, uptime, evaluation,
            stat_date, timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        hostname, max_clients, avg_mbps, max_mbps, load_ratio, peak_load_ratio,
        branch, peak_end.strftime("%Y-%m-%d %H:%M:%S"),
        ip, frequency, firmware, uptime, evaluation,
        today_str, timestamp
    ))
    sectors_conn.commit()
    print(f"✅ {hostname}: clients={max_clients}, avg={avg_mbps}, max={max_mbps}, eval=({evaluation})")

zbx_cur.close()
>>>>>>> 84d317f ( النسخة الثانية:)
zabbix_conn.close()
sectors_conn.close()
