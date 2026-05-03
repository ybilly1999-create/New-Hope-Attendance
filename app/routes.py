"""Public (member-facing) routes."""
from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify, abort, redirect, url_for, flash

from .models import db, Member, Attendance, Visitor, Setting
from .utils import determine_status, hk_now, upcoming_sunday, status_label

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Member-facing home: pick service date and check in."""
    today = date.today()
    # If today is Sunday, use today; otherwise next Sunday
    target_date = today if today.weekday() == 6 else upcoming_sunday(today)
    members = Member.query.filter_by(is_active=True).order_by(Member.member_no).all()
    # Already checked-in today?
    todays = (
        Attendance.query.filter_by(service_date=target_date)
        .order_by(Attendance.check_in_time.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "index.html",
        members=members,
        target_date=target_date,
        recent=todays,
    )


@bp.route("/checkin", methods=["POST"])
def checkin():
    """Member self check-in."""
    member_id = request.form.get("member_id", type=int)
    service_date_str = request.form.get("service_date") or date.today().isoformat()
    method = request.form.get("method", "self")
    try:
        service_d = datetime.strptime(service_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("日期格式錯誤", "error")
        return redirect(url_for("main.index"))

    if not member_id:
        flash("請先選擇姓名", "error")
        return redirect(url_for("main.index"))

    member = db.session.get(Member, member_id)
    if not member or not member.is_active:
        flash("找不到此會員", "error")
        return redirect(url_for("main.index"))

    # Check duplicate
    existing = Attendance.query.filter_by(
        member_id=member.id, service_date=service_d
    ).first()
    if existing:
        flash(f"{member.name} 已於 {service_d} 簽到（{status_label(existing.status)}）", "info")
        return redirect(url_for("main.success", member_id=member.id, date=service_d.isoformat()))

    now = hk_now()
    status = determine_status(now, service_d)
    record = Attendance(
        member_id=member.id,
        service_date=service_d,
        status=status,
        check_in_time=now,
        method=method,
    )
    db.session.add(record)
    db.session.commit()
    return redirect(url_for("main.success", member_id=member.id, date=service_d.isoformat()))


@bp.route("/success")
def success():
    """Confirmation page after check-in."""
    member_id = request.args.get("member_id", type=int)
    d = request.args.get("date")
    member = db.session.get(Member, member_id) if member_id else None
    if not member:
        return redirect(url_for("main.index"))
    try:
        service_d = datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        service_d = date.today()
    record = Attendance.query.filter_by(
        member_id=member.id, service_date=service_d
    ).first()
    return render_template("success.html", member=member, record=record, service_date=service_d)


@bp.route("/qr/<member_no>")
def qr_checkin(member_no):
    """QR-code landing page: opens with member pre-selected, one tap to confirm."""
    member = Member.query.filter_by(member_no=member_no.zfill(3), is_active=True).first()
    if not member:
        abort(404)
    today = date.today()
    target_date = today if today.weekday() == 6 else upcoming_sunday(today)
    existing = Attendance.query.filter_by(
        member_id=member.id, service_date=target_date
    ).first()
    return render_template(
        "qr_confirm.html",
        member=member,
        target_date=target_date,
        existing=existing,
    )


@bp.route("/visitor", methods=["GET", "POST"])
def visitor():
    """新朋友登記 (also usable by members for guests they bring)."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        is_anon = request.form.get("is_anonymous") == "1"
        is_child = request.form.get("is_child") == "1"
        contact = request.form.get("contact", "").strip()
        invited_by = request.form.get("invited_by", "").strip()
        note = request.form.get("note", "").strip()
        d_str = request.form.get("service_date") or date.today().isoformat()
        try:
            service_d = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            service_d = date.today()

        if not is_anon and not name:
            flash("請填寫姓名，或選擇「不記名」", "error")
            return redirect(url_for("main.visitor"))

        v = Visitor(
            name=name or None,
            is_anonymous=is_anon,
            is_child=is_child,
            contact=contact or None,
            invited_by=invited_by or None,
            note=note or None,
            service_date=service_d,
        )
        db.session.add(v)
        db.session.commit()
        flash("感謝您！願主祝福您。", "success")
        return redirect(url_for("main.index"))

    today = date.today()
    target_date = today if today.weekday() == 6 else upcoming_sunday(today)
    return render_template("visitor.html", target_date=target_date)


@bp.route("/healthz")
def healthz():
    return {"status": "ok"}, 200
