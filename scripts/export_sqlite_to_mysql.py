"""
DealSpark - Export SQLite Data to MySQL Migration SQL Script
Exports existing categories, merchants, users, products, price histories, and clicks
from the local SQLite database (instance/dealspark.db) into a production-ready MySQL SQL script.
"""
import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'instance' / 'dealspark.db'
OUTPUT_SQL_PATH = BASE_DIR / 'scripts' / 'dealspark_mysql_dump.sql'


def escape_sql_val(val):
    if val is None:
        return 'NULL'
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, bool):
        return '1' if val else '0'
    val_str = str(val).replace('\\', '\\\\').replace("'", "\\'")
    return f"'{val_str}'"


def export_sqlite_to_mysql():
    if not DB_PATH.exists():
        print(f"[ERROR] Database file not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    tables_in_order = [
        'categories',
        'merchants',
        'users',
        'products',
        'product_price_history',
        'outbound_clicks',
        'favorites'
    ]

    sql_lines = [
        "-- DealSpark Production MySQL Data Migration Script",
        "-- Generated automatically from existing DealSpark database",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "START TRANSACTION;",
        ""
    ]

    total_rows = 0

    for table in tables_in_order:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns_info = cursor.fetchall()
            if not columns_info:
                continue

            col_names = [col['name'] for col in columns_info]
            quoted_cols = ", ".join(f"`{c}`" for c in col_names)

            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()

            if not rows:
                continue

            sql_lines.append(f"-- Data for table `{table}` ({len(rows)} records)")
            for row in rows:
                values_escaped = [escape_sql_val(row[col]) for col in col_names]
                vals_str = ", ".join(values_escaped)
                sql_lines.append(
                    f"INSERT INTO `{table}` ({quoted_cols}) VALUES ({vals_str}) "
                    f"ON DUPLICATE KEY UPDATE id=id;"
                )
                total_rows += 1

            sql_lines.append("")
        except Exception as e:
            print(f"[WARNING] Skipping table {table}: {e}")

    sql_lines.extend([
        "COMMIT;",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "-- End of Migration Dump"
    ])

    with open(OUTPUT_SQL_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_lines) + "\n")

    print(f"[SUCCESS] Exported {total_rows} records across tables to {OUTPUT_SQL_PATH}")
    return True


if __name__ == '__main__':
    export_sqlite_to_mysql()
