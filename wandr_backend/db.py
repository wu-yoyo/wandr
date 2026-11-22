"""Wandr data models. Flask-SQLAlchemy 3.x / SQLAlchemy 2.x.

Database schema shared by the core API and ranking/social API.
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint


db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


# Category is intentionally restricted to the two ranking groups in the MVP.
# A city includes towns; a point_of_interest includes parks and attractions.
CATEGORIES = ("city", "point_of_interest")
SENTIMENTS = ("good", "neutral", "bad")


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    visits = db.relationship("Visit", back_populates="user", cascade="all, delete-orphan")
    wishlists = db.relationship("WantToGo", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "username": self.username, "display_name": self.display_name}


class Destination(db.Model):
    __tablename__ = "destinations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    # city = cities and towns; point_of_interest = parks, monuments, attractions, etc.
    category = db.Column(db.String(30), nullable=False, index=True)
    subtype = db.Column(db.String(60))  # e.g. national_park, state_park, museum, monument
    state = db.Column(db.String(80))
    country = db.Column(db.String(80), nullable=False, default="United States")
    description = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    parent_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=True)
    parent = db.relationship("Destination", remote_side=[id], backref="children")
    external_source = db.Column(db.String(50))
    external_id = db.Column(db.String(150))

    __table_args__ = (
        CheckConstraint("category IN ('city', 'point_of_interest')", name="ck_destination_category"),
        UniqueConstraint("external_source", "external_id", name="uq_destination_external_identity"),
    )

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "subtype": self.subtype, "state": self.state, "country": self.country,
            "description": self.description, "latitude": self.latitude,
            "longitude": self.longitude, "image_url": self.image_url,
            "parent_id": self.parent_id,
        }


class Visit(db.Model):
    """One current ranked visit per (user, destination).

    rank_position is 1-based within (user, category, sentiment).
    A change of sentiment or category requires reindexing the affected rankings.
    rank_position is nullable until a visit is inserted into the ranking.
    """
    __tablename__ = "visits"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=False, index=True)
    sentiment = db.Column(db.String(10), nullable=False)
    rank_position = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text)
    visited_at = db.Column(db.Date)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="visits")
    destination = db.relationship("Destination")

    __table_args__ = (
        UniqueConstraint("user_id", "destination_id", name="uq_visit_user_destination"),
        CheckConstraint("sentiment IN ('good', 'neutral', 'bad')", name="ck_visit_sentiment"),
        CheckConstraint("rank_position IS NULL OR rank_position >= 1", name="ck_visit_rank_positive"),
    )

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id, "destination_id": self.destination_id,
            "sentiment": self.sentiment, "rank_position": self.rank_position,
            "notes": self.notes, "visited_at": self.visited_at.isoformat() if self.visited_at else None,
            "destination": self.destination.to_dict() if self.destination else None,
        }


class WantToGo(db.Model):
    __tablename__ = "want_to_go"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="wishlists")
    destination = db.relationship("Destination")
    __table_args__ = (UniqueConstraint("user_id", "destination_id", name="uq_wishlist"),)

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "destination_id": self.destination_id,
                "destination": self.destination.to_dict()}


class Follow(db.Model):
    __tablename__ = "follows"
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    following_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    follower = db.relationship("User", foreign_keys=[follower_id])
    following = db.relationship("User", foreign_keys=[following_id])
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follow"),
        CheckConstraint("follower_id != following_id", name="ck_no_self_follow"),
    )


class Post(db.Model):
    """A feed item published when a user shares a destination ranking/visit.

    Store the linked visit; don't duplicate ranking scores in the post.
    If a visit is deleted, its posts are deleted too.
    """
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    caption = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user = db.relationship("User")
    visit = db.relationship("Visit", backref=db.backref("posts", cascade="all, delete-orphan", passive_deletes=True))
    comments = db.relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "visit_id": self.visit_id,
                "caption": self.caption, "created_at": self.created_at.isoformat(),
                "visit": self.visit.to_dict()}


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    post = db.relationship("Post", back_populates="comments")
    user = db.relationship("User")

    def to_dict(self):
        return {"id": self.id, "post_id": self.post_id, "user_id": self.user_id,
                "text": self.text, "created_at": self.created_at.isoformat()}


class Badge(db.Model):
    """Badge definitions; example: 5 national parks visited."""
    __tablename__ = "badges"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    # Rule types MVP: total_visits, subtype_visits, state_visits.
    rule_type = db.Column(db.String(30), nullable=False)
    rule_value = db.Column(db.String(80))  # e.g. national_park / California; null for total_visits
    target_count = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {"id": self.id, "code": self.code, "name": self.name,
                "description": self.description, "rule_type": self.rule_type,
                "rule_value": self.rule_value, "target_count": self.target_count}


class UserBadge(db.Model):
    """Tracks earned badges; unearned progress is computed from Visit rows."""
    __tablename__ = "user_badges"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"), nullable=False)
    earned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    badge = db.relationship("Badge")
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),)
