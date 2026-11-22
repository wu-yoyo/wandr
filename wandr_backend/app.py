"""Wandr Flask backend starter.

Person 1 owns these core routes; Person 2 can add visit/ranking/feed/comment
routes below or, preferably, in a separate routes module.

NOTE: user_id supplied by the client is a classroom prototype convention,
NOT authentication. Add real authentication/authorization before public use.
"""
import os
from flask import Flask, jsonify, request
from sqlalchemy.exc import IntegrityError
from db import db, User, Destination, Visit, WantToGo, Follow, Badge, UserBadge


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///wandr.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    @app.get("/")
    def home():
        return jsonify({"message": "Wandr API is running"})

    @app.post("/users")
    def create_user():
        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        if not username:
            return jsonify({"error": "username is required"}), 400
        user = User(username=username, display_name=data.get("display_name"))
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "username already exists"}), 409
        return jsonify(user.to_dict()), 201

    @app.get("/users/<int:user_id>")
    def get_user(user_id):
        user = db.session.get(User, user_id)
        return (jsonify(user.to_dict()), 200) if user else (jsonify({"error": "User not found"}), 404)

    @app.get("/destinations")
    def list_destinations():
        query = Destination.query
        if request.args.get("category"):
            query = query.filter_by(category=request.args["category"])
        if request.args.get("state"):
            query = query.filter_by(state=request.args["state"])
        if request.args.get("q"):
            query = query.filter(Destination.name.ilike(f"%{request.args['q']}%"))
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(100, max(1, request.args.get("per_page", 30, type=int)))
        result = query.order_by(Destination.name).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({"destinations": [d.to_dict() for d in result.items],
                        "page": page, "total": result.total, "pages": result.pages})

    @app.get("/destinations/<int:destination_id>")
    def get_destination(destination_id):
        destination = db.session.get(Destination, destination_id)
        return (jsonify(destination.to_dict()), 200) if destination else (jsonify({"error": "Destination not found"}), 404)

    @app.get("/users/<int:user_id>/wishlist")
    def list_wishlist(user_id):
        if db.session.get(User, user_id) is None:
            return jsonify({"error": "User not found"}), 404
        items = WantToGo.query.filter_by(user_id=user_id).order_by(WantToGo.created_at.desc()).all()
        return jsonify([item.to_dict() for item in items])

    @app.post("/users/<int:user_id>/wishlist")
    def add_wishlist(user_id):
        data = request.get_json(silent=True) or {}
        destination_id = data.get("destination_id")
        if db.session.get(User, user_id) is None or not isinstance(destination_id, int) or isinstance(destination_id, bool) or db.session.get(Destination, destination_id) is None:
            return jsonify({"error": "Valid user and destination_id are required"}), 400
        if WantToGo.query.filter_by(user_id=user_id, destination_id=destination_id).first():
            return jsonify({"error": "Already in wishlist"}), 409
        item = WantToGo(user_id=user_id, destination_id=destination_id)
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201

    @app.delete("/users/<int:user_id>/wishlist/<int:destination_id>")
    def remove_wishlist(user_id, destination_id):
        item = WantToGo.query.filter_by(user_id=user_id, destination_id=destination_id).first()
        if not item:
            return jsonify({"error": "Wishlist item not found"}), 404
        db.session.delete(item)
        db.session.commit()
        return "", 204

    @app.post("/users/<int:user_id>/follow")
    def follow_user(user_id):
        data = request.get_json(silent=True) or {}
        following_id = data.get("following_id")
        if (not isinstance(following_id, int) or isinstance(following_id, bool)
            or user_id == following_id or db.session.get(User, user_id) is None
            or db.session.get(User, following_id) is None):
            return jsonify({"error": "Valid, distinct users required"}), 400
        if Follow.query.filter_by(follower_id=user_id, following_id=following_id).first():
            return jsonify({"error": "Already following"}), 409
        db.session.add(Follow(follower_id=user_id, following_id=following_id))
        db.session.commit()
        return jsonify({"follower_id": user_id, "following_id": following_id}), 201

    @app.delete("/users/<int:user_id>/follow/<int:following_id>")
    def unfollow_user(user_id, following_id):
        row = Follow.query.filter_by(follower_id=user_id, following_id=following_id).first()
        if not row:
            return jsonify({"error": "Follow not found"}), 404
        db.session.delete(row)
        db.session.commit()
        return "", 204

    @app.get("/users/<int:user_id>/following")
    def list_following(user_id):
        if db.session.get(User, user_id) is None:
            return jsonify({"error": "User not found"}), 404
        rows = Follow.query.filter_by(follower_id=user_id).all()
        return jsonify([row.following.to_dict() for row in rows])

    @app.get("/users/<int:user_id>/map")
    def map_data(user_id):
        """Return pins for self/followed friends without selecting a map provider.

        ?scope=self (default), ?scope=friends, ?scope=all, or ?scope=user&friend_id=N
        ?list=visited (default), ?list=wishlist, or ?list=both
        """
        if db.session.get(User, user_id) is None:
            return jsonify({"error": "User not found"}), 404
        scope = request.args.get("scope", "self")
        list_type = request.args.get("list", "visited")
        if scope not in ("self", "friends", "all", "user") or list_type not in ("visited", "wishlist", "both"):
            return jsonify({"error": "Invalid scope or list"}), 400
        following_ids = [f.following_id for f in Follow.query.filter_by(follower_id=user_id).all()]
        if scope == "self":
            ids = [user_id]
        elif scope == "friends":
            ids = following_ids
        elif scope == "all":
            ids = [user_id] + following_ids
        else:
            friend_id = request.args.get("friend_id", type=int)
            if friend_id not in following_ids:
                return jsonify({"error": "friend_id must be a followed user"}), 400
            ids = [friend_id]
        if not ids:
            return jsonify([])
        pins = []
        if list_type in ("visited", "both"):
            for visit in Visit.query.filter(Visit.user_id.in_(ids)).all():
                pins.append({"user_id": visit.user_id, "list": "visited", "sentiment": visit.sentiment,
                             "rank_position": visit.rank_position, "destination": visit.destination.to_dict()})
        if list_type in ("wishlist", "both"):
            for item in WantToGo.query.filter(WantToGo.user_id.in_(ids)).all():
                pins.append({"user_id": item.user_id, "list": "wishlist", "destination": item.destination.to_dict()})
        return jsonify(pins)

    @app.get("/users/<int:user_id>/badges")
    def badge_progress(user_id):
        """Compute current badge progress; earning/awarding badge is future work."""
        if db.session.get(User, user_id) is None:
            return jsonify({"error": "User not found"}), 404
        visits = Visit.query.filter_by(user_id=user_id).all()
        earned = {row.badge_id for row in UserBadge.query.filter_by(user_id=user_id).all()}
        result = []
        for badge in Badge.query.order_by(Badge.id).all():
            if badge.rule_type == "total_visits":
                count = len(visits)
            elif badge.rule_type == "subtype_visits":
                count = sum(v.destination.subtype == badge.rule_value for v in visits)
            elif badge.rule_type == "state_visits":
                count = sum(v.destination.state == badge.rule_value for v in visits)
            else:
                count = 0
            result.append({**badge.to_dict(), "progress": count,
                           "completed": count >= badge.target_count,
                           "awarded": badge.id in earned})
        return jsonify(result)

    # Person 2: add visit creation, pairwise insertion/reordering, post creation,
    # friends' feed and comments here (or import a Blueprint from routes_social.py).

    # Prototype-only schema initialization. For real deployed databases, use migrations.
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
