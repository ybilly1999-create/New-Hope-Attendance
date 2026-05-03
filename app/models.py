"""Database models."""
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Member(db.Model):
    """Church member."""
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    member_no = db.Column(db.String(10), unique=True, nullable=False, index=True)  # e.g. "007"
    name = db.Column(db.String(50), nullable=False, index=True)  # 中文姓名
    english_name = db.Column(db.String(50), nullable=True)
    note = db.Column(db.String(200), nullable=True)  # 備註，例：兒童、牧師、家屬
    is_child = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendance_records = db.relationship(
        "Attendance", backref="member", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "member_no": self.member_no,
            "name": self.name,
            "english_name": self.english_name,
            "note": self.note,
            "is_child": self.is_child,
            "is_active": self.is_active,
        }

    @property
    def display_name(self):
        return f"{self.member_no} {self.name}"


class Attendance(db.Model):
    """Single attendance record. One per member per service date."""
    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("member_id", "service_date", name="uq_member_service"),
    )

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, index=True)
    service_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)  # 'on_time' | 'late'
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(20), default="manual")  # 'self', 'qr', 'manual'
    note = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "member_id": self.member_id,
            "member_no": self.member.member_no if self.member else None,
            "name": self.member.name if self.member else None,
            "service_date": self.service_date.isoformat(),
            "status": self.status,
            "check_in_time": self.check_in_time.isoformat() if self.check_in_time else None,
            "method": self.method,
            "note": self.note,
        }


class Visitor(db.Model):
    """新朋友 / 訪客 (non-member visitor)."""
    __tablename__ = "visitors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)  # 可不記名
    service_date = db.Column(db.Date, nullable=False, index=True)
    is_anonymous = db.Column(db.Boolean, default=False)  # 不記名
    is_child = db.Column(db.Boolean, default=False)
    contact = db.Column(db.String(200), nullable=True)
    invited_by = db.Column(db.String(100), nullable=True)  # 邀請人
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name if not self.is_anonymous else "不記名",
            "service_date": self.service_date.isoformat(),
            "is_anonymous": self.is_anonymous,
            "is_child": self.is_child,
            "contact": self.contact,
            "invited_by": self.invited_by,
            "note": self.note,
        }


class Setting(db.Model):
    """Generic key-value settings."""
    __tablename__ = "settings"

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(500), nullable=True)

    @classmethod
    def get(cls, key, default=None):
        row = db.session.get(cls, key)
        return row.value if row else default

    @classmethod
    def set(cls, key, value):
        row = db.session.get(cls, key)
        if row:
            row.value = value
        else:
            db.session.add(cls(key=key, value=value))
