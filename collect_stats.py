#!/usr/bin/env python3
import sys
import argparse
from datetime import datetime, timedelta

import mysql.connector
import pymysql
import pytz


# =========================
# CONFIG (keep simple)
# =========================
ZABBIX_DB = {
    "host": "172.31.1.36",
    "user": "wnet",
    "password": "#Wnet2025",
    "database": "zabbix_db",
}

SECTORS_DB_HOST = "localhost"
SECTORS_DB_PORT = 3307
SECTORS_DB_USER = "root"
SECTORS_DB_PASS = "strongpass123"
SECTORS_DB_NAME = "Sectors"
SECTORS_DB_CHARSET = "utf8mb4"
SECTORS_DB_COLLATION = "utf8mb4_general_ci"

TZ_NAME = "Africa/Tripoli"


# =========================
# DB INIT (create DB + tables if missing)
# =========================
def _connect_server_no_db():
    return pymysql.connect(
        host=SECTORS_DB_HOST,
        port=SECTORS_DB_PORT,
        user=SECTORS_DB_USER,
        password=SECTORS_DB_PASS,
        charset=SECTORS_DB_CHARSET,
        autocommit=True,
    )


def _connect_sectors_db():
    return pymysql.connect(
        host=SECTORS_DB_HOST,
        port=SECTORS_DB_PORT,
        user=SECTORS_DB_USER,
        password=SECTORS_DB_PASS,
        database=SECTORS_DB_NAME,
        charset=SECTORS_DB_CHARSET,
        autocommit=True,
    )


def ensure_sectors_database_and_tables():
    # 1) Create database if missing
    srv = _connect_server_no_db()
    try:
        with srv.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{SECTORS_DB_NAME}` "
                f"CHARACTER SET {SECTORS_DB_CHARSET} "
                f"COLLATE {SECTORS_DB_COLLATION};"
            )
    finally:
        srv.close()

    # 2) Create tables if missing
    db = _connect_sectors_db()
    try:
        with db.cursor() as cur:
            # sector_stats table (matches your INSERT columns)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sector_stats (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    hostname VARCHAR(128) NOT NULL,
                    max_clients INT NULL,
                    avg_mbps DECIMAL(10,2) NULL,
                    max_mbps DECIMAL(10,2) NULL,
                    load_ratio DECIMAL(10,2) NULL,
                    peak_load_ratio DECIMAL(10,2) NULL,
                    branch VARCHAR(128) NULL,
                    last_updated DATETIME NULL,
                    ip VARCHAR(64) NULL,
                    frequency VARCHAR(64) NULL,
                    firmware_version VARCHAR(128) NULL,
                    uptime BIGINT NULL,
                    evaluation VARCHAR(255) NULL,
                    stat_date DATE NULL,
                    `timestamp` DATETIME NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    INDEX idx_stat_date (stat_date),
                    INDEX idx_branch (branch),
                    INDEX idx_hostname (hostname),
                    INDEX idx_last_updated (last_updated)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            # collector_runs table (optional but very useful للتتبع)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS collector_runs (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    started_at DATETIME NOT NULL,
                    ended_at DATETIME NULL,
                    peak_start DATETIME NULL,
                    peak_end DATETIME NULL,
                    sectors_found INT NULL,
                    inserted_rows INT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'running',
                    error TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    INDEX idx_started_at (started_at),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
    finally:
        db.close()


# =========================
# Business logic
# =========================
def evaluate_sector(avg_mbps, max_clients):
    statuses = []

    # لا توجد بيانات إطلاقًا
    if (avg_mbps is None or avg_mbps == 0) and (max_clients is None or max_clients == 0):
        return "⚫ بلا بيانات"

    if avg_mbps is not None and avg_mbps < 5:
        statuses.append("🔴 ضعيف جدًا")

    if max_clients is not None and max_clients > 25:
        statuses.append("🟠 ازدحام")

    if max_clients is not None and max_clients <= 5:
        statuses.append("🔵 يحتاج دعم")

    if avg_mbps is not None and 5 <= avg_mbps <= 10:
        statuses.append("🟡 متذبذب")

    if (max_clients is not None) and (avg_mbps is not None) and (5 <= max_clients <= 25) and (avg_mbps > 15):
        statuses.append("🟢 جيد")

    return ", ".join(statuses) if statuses else "🟠 غير مصنف"


def get_ip_address(zabbix_conn, hostid):
    cur = zabbix_conn.cursor()
    cur.execute("SELECT ip FROM interface WHERE hostid = %s LIMIT 1", (hostid,))
    row = cur.fetchone()
    return row[0] if row else ""


def get_string_value(zabbix_conn, hostid, key):
    cur = zabbix_conn.cursor()
    cur.execute(
        """
        SELECT hi.value
        FROM items i
        JOIN history_str hi ON hi.itemid = i.itemid
        WHERE i.hostid = %s AND i.key_ = %s
        ORDER BY hi.clock DESC
        LIMIT 1
        """,
        (hostid, key),
    )
    row = cur.fetchone()
    return row[0] if row else ""


def get_uint_value(zabbix_conn, hostid, key):
    cur = zabbix_conn.cursor()
    cur.execute(
        """
        SELECT hu.value
        FROM items i
        JOIN history_uint hu ON hu.itemid = i.itemid
        WHERE i.hostid = %s AND i.key_ = %s
        ORDER BY hu.clock DESC
        LIMIT 1
        """,
        (hostid, key),
    )
    row = cur.fetchone()
    return row[0] if row else 0


def run_collector():
    # Always ensure DB/tables exist first (first run / restore safe)
    ensure_sectors_database_and_tables()

    tz = pytz.timezone(TZ_NAME)
    now = datetime.now(tz)
    today_midnight = datetime.combine(now.date(), datetime.min.time()).astimezone(tz)
    peak_start = today_midnight - timedelta(hours=4)
    peak_end = today_midnight
    today_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%d %H:%M:%S")

    print(f"📆 Peak window: {peak_start} → {peak_end}")

    # Connect Zabbix
    zabbix_conn = mysql.connector.connect(**ZABBIX_DB)
    sectors_conn = _connect_sectors_db()

    run_id = None
    inserted = 0
    try:
        # Create run record
        with sectors_conn.cursor() as c:
            c.execute(
                """
                INSERT INTO collector_runs (started_at, peak_start, peak_end, status)
                VALUES (%s, %s, %s, 'running')
                """,
                (ts_str, peak_start.strftime("%Y-%m-%d %H:%M:%S"), peak_end.strftime("%Y-%m-%d %H:%M:%S")),
            )
            run_id = c.lastrowid

        zbx_cur = zabbix_conn.cursor(dictionary=True)
        zbx_cur.execute(
            f"""
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
            """
        )

        results = zbx_cur.fetchall()
        print(f"📡 Found {len(results)} sectors")

        for row in results:
            hostname = row["hostname"]
            hostid = row["hostid"]
            branch = row["branch"]
            avg_mbps = row["avg_mbps"]
            max_mbps = row["max_mbps"]
            max_clients = row["max_clients"]
            load_ratio = row["load_ratio"]
            peak_load_ratio = row["peak_load_ratio"]

            ip = get_ip_address(zabbix_conn, hostid)

            band_raw = get_string_value(zabbix_conn, hostid, "ssid.band[mtxrWlApBand.1]")
            frequency = band_raw.split("/")[0] if (band_raw and "/" in band_raw) else (band_raw or "")

            firmware = get_string_value(zabbix_conn, hostid, "system.hw.firmware")
            uptime = get_uint_value(zabbix_conn, hostid, "system.uptime[sysUpTime.0]")

            evaluation = evaluate_sector(avg_mbps, max_clients)

            with sectors_conn.cursor() as cur2:
                cur2.execute(
                    """
                    INSERT INTO sector_stats (
                        hostname, max_clients, avg_mbps, max_mbps, load_ratio, peak_load_ratio,
                        branch, last_updated, ip, frequency, firmware_version, uptime, evaluation,
                        stat_date, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        hostname,
                        max_clients,
                        avg_mbps,
                        max_mbps,
                        load_ratio,
                        peak_load_ratio,
                        branch,
                        peak_end.strftime("%Y-%m-%d %H:%M:%S"),
                        ip,
                        frequency,
                        firmware,
                        uptime,
                        evaluation,
                        today_str,
                        ts_str,
                    ),
                )

            inserted += 1
            print(f"✅ {hostname}: clients={max_clients}, avg={avg_mbps}, max={max_mbps}, eval=({evaluation})")

        # update run record
        with sectors_conn.cursor() as c:
            c.execute(
                """
                UPDATE collector_runs
                SET ended_at=%s, sectors_found=%s, inserted_rows=%s, status='ok'
                WHERE id=%s
                """,
                (datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"), len(results), inserted, run_id),
            )

        zbx_cur.close()

    except Exception as e:
        # mark run failed
        try:
            if run_id is not None:
                with sectors_conn.cursor() as c:
                    c.execute(
                        """
                        UPDATE collector_runs
                        SET ended_at=%s, inserted_rows=%s, status='failed', error=%s
                        WHERE id=%s
                        """,
                        (
                            datetime.now(pytz.timezone(TZ_NAME)).strftime("%Y-%m-%d %H:%M:%S"),
                            inserted,
                            str(e),
                            run_id,
                        ),
                    )
        except Exception:
            pass
        raise

    finally:
        try:
            zabbix_conn.close()
        except Exception:
            pass
        try:
            sectors_conn.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Sector stats collector (auto-create DB/tables if missing)")
    ap.add_argument(
        "--init-only",
        action="store_true",
        help="Only create Sectors DB + tables if missing, then exit",
    )
    args = ap.parse_args()

    if args.init_only:
        ensure_sectors_database_and_tables()
        print("✅ OK: Sectors DB + tables ensured (init-only).")
        return 0

    run_collector()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
