"""Small verified-by-team sample dataset; expand via a reviewed CSV later.

Run: python seed.py
"""
from app import app
from db import db, Destination, Badge

DESTINATIONS = [
    ("New York City", "city", "city", "New York", 40.7128, -74.0060, None),
    ("San Francisco", "city", "city", "California", 37.7749, -122.4194, None),
    ("Washington, D.C.", "city", "city", "District of Columbia", 38.9072, -77.0369, None),
    ("Ithaca", "city", "town", "New York", 42.4430, -76.5019, None),
    ("Yosemite National Park", "point_of_interest", "national_park", "California", 37.7456, -119.5936, None),
    ("Yellowstone National Park", "point_of_interest", "national_park", "Wyoming", 44.4280, -110.5885, None),
    ("Grand Canyon National Park", "point_of_interest", "national_park", "Arizona", 36.1069, -112.1129, None),
    ("Statue of Liberty", "point_of_interest", "monument", "New York", 40.6892, -74.0445, "New York City"),
    ("Golden Gate Bridge", "point_of_interest", "landmark", "California", 37.8199, -122.4783, "San Francisco"),
    ("Central Park", "point_of_interest", "urban_park", "New York", 40.7829, -73.9654, "New York City"),
]
BADGES = [
    ("first_step", "First Steps", "Visit your first destination", "total_visits", None, 1),
    ("explorer_10", "Explorer", "Visit 10 destinations", "total_visits", None, 10),
    ("parks_5", "National Parks Explorer", "Visit 5 national parks", "subtype_visits", "national_park", 5),
    ("california_5", "California Explorer", "Visit 5 places in California", "state_visits", "California", 5),
]

with app.app_context():
    by_name = {d.name: d for d in Destination.query.all()}
    for name, category, subtype, state, latitude, longitude, parent_name in DESTINATIONS:
        if name not in by_name:
            dest = Destination(name=name, category=category, subtype=subtype, state=state,
                               latitude=latitude, longitude=longitude, country="United States")
            db.session.add(dest)
            by_name[name] = dest
    db.session.flush()
    for name, _, _, _, _, _, parent_name in DESTINATIONS:
        if parent_name:
            by_name[name].parent_id = by_name[parent_name].id
    for code, name, description, rule_type, rule_value, target in BADGES:
        if Badge.query.filter_by(code=code).first() is None:
            db.session.add(Badge(code=code, name=name, description=description,
                                 rule_type=rule_type, rule_value=rule_value, target_count=target))
    db.session.commit()
    print("Seed complete; destinations:", Destination.query.count(), "badges:", Badge.query.count())
