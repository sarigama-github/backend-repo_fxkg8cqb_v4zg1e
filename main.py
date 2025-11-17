import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User, Car, Listing, Booking, Review

app = FastAPI(title="RAKB API", description="Rental Agency platform for cars and renters in Morocco")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"name": "RAKB API", "status": "ok"}


# ---------- Public browse/search ----------
class ListingQuery(BaseModel):
    city: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = 24


@app.post("/api/listings")
def list_listings(query: ListingQuery):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    filt: dict = {}
    if query.city:
        # case-insensitive exact match for city
        filt["city"] = {"$regex": f"^{query.city}$", "$options": "i"}

    price_filter = {}
    if query.min_price is not None:
        price_filter["$gte"] = query.min_price
    if query.max_price is not None:
        price_filter["$lte"] = query.max_price
    if price_filter:
        filt["daily_price"] = price_filter

    docs = get_documents("listing", filt, limit=query.limit)

    # Shape results: ensure consistent id string
    items = []
    for d in docs:
        d = dict(d)
        d["id"] = str(d.pop("_id", ""))
        # try to enrich with car basic fields if available
        try:
            if d.get("car_id"):
                car = db["car"].find_one({"_id": ObjectId(d["car_id"])})
                if car:
                    car["id"] = str(car.pop("_id", ""))
                    d["car"] = car
        except Exception:
            pass
        items.append(d)

    return {"items": items}


@app.get("/api/listings/{listing_id}")
def get_listing_detail(listing_id: str):
    """Fetch a single listing by id, including its car details."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        lst = db["listing"].find_one({"_id": ObjectId(listing_id)})
        if not lst:
            raise HTTPException(status_code=404, detail="Listing not found")
        lst = dict(lst)
        lst["id"] = str(lst.pop("_id", ""))
        # attach car
        car_doc = None
        try:
            if lst.get("car_id"):
                car_doc = db["car"].find_one({"_id": ObjectId(lst["car_id"])})
        except Exception:
            car_doc = None
        if car_doc:
            car_doc = dict(car_doc)
            car_doc["id"] = str(car_doc.pop("_id", ""))
            lst["car"] = car_doc
        return lst
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id format")


@app.get("/api/cities")
def get_cities():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    cities = db["listing"].distinct("city")
    cities = sorted([c for c in cities if isinstance(c, str)])
    return {"items": cities}


# ---------- Minimal creation endpoints (for seeding/demo) ----------
@app.post("/api/users", status_code=201)
def create_user(user: User):
    user_id = create_document("user", user)
    return {"id": user_id}


@app.post("/api/cars", status_code=201)
def create_car(car: Car):
    car_id = create_document("car", car)
    return {"id": car_id}


@app.post("/api/listing", status_code=201)
def create_listing(listing: Listing):
    listing_id = create_document("listing", listing)
    return {"id": listing_id}


@app.post("/api/bookings", status_code=201)
def create_booking(booking: Booking):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Basic overlap check using ISO date strings or date objects
    overlap = db["booking"].find_one({
        "listing_id": booking.listing_id,
        "$or": [
            {
                "start_date": {"$lte": booking.end_date},
                "end_date": {"$gte": booking.start_date},
            }
        ],
    })
    if overlap:
        raise HTTPException(status_code=400, detail="Dates not available")

    booking_id = create_document("booking", booking)
    return {"id": booking_id}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
