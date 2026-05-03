"""Lightweight JSON API for AJAX use."""
from datetime import date, datetime
from flask import Blueprint, jsonify, request

from .models import db, Member, Attendance

api_bp = Blueprint("api", __name__)


@api_bp.route("/members")
def members():
    """For autocomplete/search on the check-in page."""
    q = request.args.get("q", "").strip().lower()
    query = Member.query.filter_by(is_active=True)
    items = query.order_by(Member.member_no).all()
    if q:
        items = [
            m for m in items
            if q in m.name.lower()
            or q in (m.english_name or "").lower()
            or q in m.member_no.lower()
        ]
    return jsonify([m.to_dict() for m in items[:50]])
