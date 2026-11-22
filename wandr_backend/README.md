# Wandr backend starter

## Setup

```bash
cd wandr_backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python app.py
```

`GET http://127.0.0.1:5000/` should say the API is running.

## Sample calls

```bash
curl http://127.0.0.1:5000/destinations
curl -X POST http://127.0.0.1:5000/users -H 'Content-Type: application/json' -d '{"username":"traveler1"}'
curl -X POST http://127.0.0.1:5000/users/1/wishlist -H 'Content-Type: application/json' -d '{"destination_id":1}'
curl http://127.0.0.1:5000/users/1/map?scope=self
curl http://127.0.0.1:5000/users/1/badges
```

## Ranking contract for Person 2

- Two independent categories: `city` (cities/towns) and `point_of_interest` (parks, landmarks, attractions).
- Within each category, there are three ordered sentiment tiers: `good`, `neutral`, `bad`.
- `Visit.rank_position` is **1-based within (user, category, sentiment)**; lower number is better.
- Overall display sorts categories separately, then sentiments in `good`, `neutral`, `bad` order, then `rank_position` ascending.
- When creating a visit, choose sentiment first; compare against existing visits in that tier to insert it at a position (binary search UX). Shift displaced ranks to maintain contiguous positions. Updating/reranking should shift positions too. Handle deletion and sentiment changes by reindexing affected tiers.
- Commit a whole reorder atomically; use a transaction and tests, and never rely on a rank-position uniqueness constraint during intermediate shifts.
- Every user/destination pair has at most one current `Visit`; add `Comparison` history later only if needed.
- `Post` represents a published visit/rank update. `Comment` is attached to a `Post`. Decide whether every visit automatically publishes or the user opts in.
- Map data endpoint returns pins with latitude/longitude for a frontend map UI; it does not render the map.
- Badge `/users/<id>/badges` calculates live progress. `UserBadge` can record awards once Person 2 implements an awarding action.

## Ownership

Person 1: `db.py`, seed data, users/destinations/wishlist/follow/map routes, deployment.
Person 2: visit CRUD, ranking & comparisons, published posts, comments, friend feed, badges awards if needed.

## Important caveats

- The APIs do not authenticate users. Treat them as a **classroom prototype only**. Do not publicly deploy with write access and fake user IDs.
- `db.create_all()` creates new tables but **does not migrate existing schema**. If you change models during local prototyping, reset the SQLite database or add migrations after coordination with your partner.
- The 10 sample destinations are examples to test the API, not a comprehensive place catalog. Import a larger reviewed CSV with stable source identifiers and accurate coordinates later; avoid bulk entry until schema and duplicate handling are finalized.
- The data model intentionally uses a single `Destination` table rather than separate city/park/attraction tables. `parent_id` supports attractions nested within cities, parks, and so on.
