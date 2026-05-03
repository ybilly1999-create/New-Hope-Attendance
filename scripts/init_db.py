"""
Initialize database and optionally seed with member list from Excel.

Usage:
  python scripts/init_db.py                  # Just create tables
  python scripts/init_db.py --seed members.xlsx  # Seed members
  python scripts/init_db.py --seed-all year_summary.xlsx  # Seed members + historical attendance
"""
import os
import sys
import argparse
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.models import db, Member, Attendance, Setting


def seed_members_from_dianming(xlsx_path):
    """Seed member list from 點名用 sheet (Shou-Dong-Chong-Bai-Dian-Ming.xlsx)."""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    if "點名用" not in wb.sheetnames:
        print(f"⚠ Sheet '點名用' not found in {xlsx_path}")
        return 0
    ws = wb["點名用"]

    added = 0
    seen = set()
    for row in ws.iter_rows(values_only=True):
        for offset in [0, 4, 8, 12]:
            if offset + 2 >= len(row):
                continue
            rid, name, eng = row[offset], row[offset + 1], row[offset + 2]
            if rid is None or name is None or not isinstance(name, str):
                continue
            if isinstance(rid, float):
                rid = str(int(rid)).zfill(3)
            else:
                rid = str(rid).strip()
                if rid.isdigit():
                    rid = rid.zfill(3)
            if rid in seen:
                continue
            seen.add(rid)

            # Skip if exists
            if Member.query.filter_by(member_no=rid).first():
                continue

            # Detect children by english_name == '兒童' or note text
            is_child = False
            note = None
            eng_str = eng.strip() if isinstance(eng, str) else None
            if eng_str == "兒童":
                is_child = True
                eng_str = None
                note = "兒童"
            elif eng_str:
                note = None

            m = Member(
                member_no=rid,
                name=name.strip(),
                english_name=eng_str,
                note=note,
                is_child=is_child,
                is_active=True,
            )
            db.session.add(m)
            added += 1
    db.session.commit()
    print(f"✓ Imported {added} members from {xlsx_path}")
    return added


# Sheets that contain a yearly attendance grid (member_no | name | note | ... | dates)
# Format observed in source workbook: 53/54 sheets sharing a near-identical layout.
YEAR_SHEETS = [
    "2017記錄",
    "2018記錄",
    "2019記錄",
    "2020記錄",
    "2021記錄",
    "2022記錄",
    "「全年總表2025」",
    "全年總表",  # current year (2026)
]


def _import_year_sheet(ws, expected_year=None):
    """Import a single year sheet. Returns (new_members, new_attendance)."""
    # 1. Find the header row containing 編號 / 姓名 (usually row 7)
    header_row = None
    for r in range(1, 15):
        if ws.cell(r, 1).value == "編號" and ws.cell(r, 2).value == "姓名":
            header_row = r
            break
    if not header_row:
        print(f"  ⚠ Could not find header row in '{ws.title}'")
        return 0, 0

    # 2. Date columns: scan row 1 for datetime cells. Filter to expected year if given.
    dates = []
    for c in range(1, ws.max_column + 1):
        v = ws.cell(1, c).value
        if isinstance(v, datetime):
            d = v.date()
            if expected_year and d.year != expected_year:
                # Skip stray cells (e.g. year-end overlap into next year is OK)
                # Only allow exact-match year, plus first week of next year
                if not (d.year == expected_year + 1 and d.month == 1 and d.day <= 7):
                    continue
            dates.append((c, d))
    if not dates:
        print(f"  ⚠ No date columns in '{ws.title}'")
        return 0, 0

    new_m = 0
    new_a = 0
    for r in range(header_row + 1, ws.max_row + 1):
        rid_raw = ws.cell(r, 1).value
        name = ws.cell(r, 2).value
        note = ws.cell(r, 3).value

        if rid_raw is None or not isinstance(name, str) or not name.strip():
            continue

        # Normalize member_no: prefer 3-digit zero-pad if it's an integer
        if isinstance(rid_raw, float):
            rid = str(int(rid_raw)).zfill(3)
        elif isinstance(rid_raw, int):
            rid = str(rid_raw).zfill(3)
        else:
            rid = str(rid_raw).strip()
            if rid.isdigit():
                rid = rid.zfill(3)

        name = name.strip()
        note_str = note.strip() if isinstance(note, str) else None

        m = Member.query.filter_by(member_no=rid).first()
        if not m:
            is_child = bool(note_str and "兒童" in note_str)
            m = Member(
                member_no=rid, name=name, note=note_str,
                is_child=is_child, is_active=True,
            )
            db.session.add(m)
            db.session.flush()
            new_m += 1
        else:
            if not m.note and note_str:
                m.note = note_str

        for col_idx, sd in dates:
            val = ws.cell(r, col_idx).value
            if val in (None, "", 0, 0.0):
                continue
            try:
                v = int(float(val))
            except (ValueError, TypeError):
                continue
            if v not in (1, 2, 3, 4):
                continue
            if v in (3, 4):
                m.is_child = True
            status = "on_time" if v in (1, 3) else "late"
            existing = Attendance.query.filter_by(member_id=m.id, service_date=sd).first()
            if existing:
                continue
            db.session.add(Attendance(
                member_id=m.id, service_date=sd, status=status,
                check_in_time=datetime.combine(sd, datetime.min.time()),
                method="import",
            ))
            new_a += 1
    db.session.commit()
    return new_m, new_a


def seed_from_year_summary(xlsx_path, sheet_name=None):
    """Seed members AND attendance from ALL year sheets in the workbook.

    If sheet_name is given, only that sheet is imported (legacy behavior).
    Otherwise, every known year sheet is imported in chronological order.
    """
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    if sheet_name:
        targets = [sheet_name] if sheet_name in wb.sheetnames else []
    else:
        targets = [s for s in YEAR_SHEETS if s in wb.sheetnames]

    if not targets:
        print(f"⚠ No year sheets found in {xlsx_path}")
        return

    print(f"Importing {len(targets)} year sheet(s) from {xlsx_path}")
    total_m = 0
    total_a = 0
    for sn in targets:
        ws = wb[sn]
        # Extract expected year from sheet name (digits like 2017, 2018, 2025)
        import re
        m_year = re.search(r"(20\d{2})", sn)
        expected_year = int(m_year.group(1)) if m_year else None
        if sn == "全年總表":
            # Current year — derive from first date cell
            for c in range(1, ws.max_column + 1):
                v = ws.cell(1, c).value
                if isinstance(v, datetime):
                    expected_year = v.date().year
                    break
        new_m, new_a = _import_year_sheet(ws, expected_year)
        print(f"  ✓ {sn} (year={expected_year}): +{new_m} members, +{new_a} attendance")
        total_m += new_m
        total_a += new_a

    print(f"✓ Imported {total_m} new members, {total_a} attendance records from {xlsx_path}")


def merge_dianming_metadata(xlsx_path):
    """Apply english_name and 兒童 flag from 點名用 sheet to existing members."""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    if "點名用" not in wb.sheetnames:
        return
    ws = wb["點名用"]
    updated = 0
    for row in ws.iter_rows(values_only=True):
        for offset in [0, 4, 8, 12]:
            if offset + 2 >= len(row):
                continue
            rid, name, eng = row[offset], row[offset + 1], row[offset + 2]
            if rid is None or not isinstance(name, str):
                continue
            if isinstance(rid, float):
                rid = str(int(rid)).zfill(3)
            else:
                rid = str(rid).strip().zfill(3) if str(rid).strip().isdigit() else str(rid).strip()
            m = Member.query.filter_by(member_no=rid).first()
            if not m:
                continue
            eng_str = eng.strip() if isinstance(eng, str) else None
            changed = False
            if eng_str == "兒童":
                if not m.is_child:
                    m.is_child = True
                    changed = True
            elif eng_str and not m.english_name:
                m.english_name = eng_str
                changed = True
            if changed:
                updated += 1
    db.session.commit()
    print(f"✓ Updated metadata for {updated} members")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-members", help="Path to Shou-Dong-Chong-Bai-Dian-Ming.xlsx")
    parser.add_argument("--seed-history", help="Path to Chong-Bai-Chu-Xi-Ji-Lu-2025-2026.xlsx")
    parser.add_argument("--reset", action="store_true", help="Drop all tables first (DANGER)")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            print("⚠ Resetting database...")
            db.drop_all()
            db.create_all()

        # Always ensure tables exist
        db.create_all()
        print(f"✓ Database ready: {app.config['SQLALCHEMY_DATABASE_URI']}")

        existing = Member.query.count()
        print(f"Current members in DB: {existing}")

        if args.seed_history and Path(args.seed_history).exists():
            seed_from_year_summary(args.seed_history)

        if args.seed_members and Path(args.seed_members).exists():
            seed_members_from_dianming(args.seed_members)
            merge_dianming_metadata(args.seed_members)

        print(f"Final members: {Member.query.count()}, attendance: {Attendance.query.count()}")


if __name__ == "__main__":
    main()
