
import mysql.connector
from datetime import datetime, timedelta
import pytz

zabbix_conn = mysql.connector.connect(
    host='172.31.1.36',
    user='wnet',
    password='#Wnet2025',
    database='zabbix_db'
)

sectors_conn = mysql.connector.connect(
    host='localhost',
    port=3307,
    user='root',
    password='strongpass123',
    database='Sectors'
)

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
zabbix_conn.close()
sectors_conn.close()
