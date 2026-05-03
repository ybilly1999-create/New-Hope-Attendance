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


def seed_from_year_summary(xlsx_path, sheet_name="全年總表"):
    """Seed members AND attendance from the year summary sheet."""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    if sheet_name not in wb.sheetnames:
        print(f"⚠ Sheet '{sheet_name}' not found")
        return
    ws = wb[sheet_name]

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 8:
        print("⚠ Sheet too short")
        return

    header = rows[0]
    # Date columns start at index 5 (column F)
    dates = []
    for i in range(5, len(header)):
        v = header[i]
        if isinstance(v, datetime):
            dates.append((i, v.date()))
    print(f"Found {len(dates)} date columns")

    # Member rows start at row 8 (index 7)
    added_m = 0
    added_a = 0
    for r in rows[7:]:
        if not r or len(r) < 3:
            continue
        rid_raw = r[0]
        name = r[1]
        note = r[2]
        if rid_raw is None or name is False or name is None or not isinstance(name, str):
            continue
        if isinstance(rid_raw, float):
            rid = str(int(rid_raw)).zfill(3)
        else:
            rid = str(rid_raw).strip()
            if rid.isdigit():
                rid = rid.zfill(3)
        name = name.strip()
        note_str = note.strip() if isinstance(note, str) else None

        m = Member.query.filter_by(member_no=rid).first()
        if not m:
            # Detect child from name list (we'll mark from manual file later)
            is_child = (note_str and "兒童" in note_str)
            m = Member(
                member_no=rid, name=name, note=note_str,
                is_child=is_child, is_active=True,
            )
            db.session.add(m)
            db.session.flush()
            added_m += 1
        else:
            # Update note if missing
            if not m.note and note_str:
                m.note = note_str

        # Attendance values: 1=adult on-time, 2=adult late, 3=child on-time, 4=child late
        for col_idx, sd in dates:
            if col_idx >= len(r):
                continue
            val = r[col_idx]
            if val in (None, "", 0):
                continue
            try:
                v = int(val)
            except (ValueError, TypeError):
                continue
            if v in (3, 4):
                m.is_child = True
            status = "on_time" if v in (1, 3) else "late" if v in (2, 4) else None
            if not status:
                continue
            existing = Attendance.query.filter_by(member_id=m.id, service_date=sd).first()
            if existing:
                continue
            db.session.add(Attendance(
                member_id=m.id, service_date=sd, status=status,
                check_in_time=datetime.combine(sd, datetime.min.time()),
                method="import",
            ))
            added_a += 1
    db.session.commit()
    print(f"✓ Imported {added_m} new members, {added_a} attendance records from {xlsx_path}")


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
