import motor.motor_asyncio
import time
from config import DB_URI, DB_NAME

# ---------------- DB CLIENT ---------------- #

dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]

user_data = database["users"]
series_catalog = database["series_catalog"]
requests_col = database["requests"]
premium_col = database["premium_users"]
invoice_col = database["premium_invoice"]

# ---------------- DEFAULT VERIFY ---------------- #

default_verify = {
    "is_verified": False,
    "verified_time": 0,
    "verify_token": "",
    "expire_time": None,
    "referrals": 0
}

# ---------------- USER ---------------- #

def new_user(uid):
    return {
        "_id": uid,
        "verify_status": default_verify.copy(),
        "referrals": 0
    }

async def present_user(user_id):
    return bool(await user_data.find_one({"_id": user_id}))

async def add_user(user_id):
    await user_data.insert_one(new_user(user_id))

# ---------------- VERIFY ---------------- #

async def get_verify_status(user_id):
    user = await user_data.find_one({"_id": user_id})
    return user.get("verify_status", default_verify.copy()) if user else default_verify.copy()

async def update_verify_status(user_id, **kwargs):
    user = await user_data.find_one({"_id": user_id})
    verify = user.get("verify_status", default_verify.copy()) if user else default_verify.copy()
    verify.update(kwargs)

    await user_data.update_one(
        {"_id": user_id},
        {"$set": {"verify_status": verify}},
        upsert=True
    )

# ---- BACKWARD COMPATIBILITY ---- #

async def db_verify_status(user_id):
    return await get_verify_status(user_id)

async def db_update_verify_status(user_id, verify):
    return await update_verify_status(user_id, **verify)

# ---------------- REFERRAL ---------------- #

async def add_referral(user_id):
    await user_data.update_one(
        {"_id": user_id},
        {"$inc": {"referrals": 1}},
        upsert=True
    )

async def get_referrals(user_id):
    u = await user_data.find_one({"_id": user_id})
    return u.get("referrals", 0) if u else 0

# ---------------- USERS ---------------- #

async def full_userbase():
    return [doc["_id"] async for doc in user_data.find()]

async def del_user(user_id):
    await user_data.delete_one({"_id": user_id})

# ---------------- PREMIUM ---------------- #

async def get_premium(user_id):
    return await premium_col.find_one({"user_id": user_id})

async def add_premium(user_id, expire_time=None):
    await premium_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "is_premium": True,
            "start_time": int(time.time()),
            "expire_time": expire_time
        }},
        upsert=True
    )

async def remove_premium(user_id):
    await premium_col.delete_one({"user_id": user_id})

# ---------------- INVOICE ---------------- #

async def add_invoice(user_id, days, admin_id):
    await invoice_col.insert_one({
        "user_id": user_id,
        "days": days,
        "time": int(time.time()),
        "admin": admin_id
    })

# ---------------- SERIES ---------------- #

async def get_series(title):
    return await series_catalog.find_one({"_id": title})

async def save_series(title, post_id, episodes):
    await series_catalog.update_one(
        {"_id": title},
        {"$set": {"post_id": post_id, "episodes": episodes}},
        upsert=True
    )

async def update_series_episodes(title, episodes):
    await series_catalog.update_one(
        {"_id": title},
        {"$set": {"episodes": episodes}}
    )

async def reset_series_catalog():
    await series_catalog.delete_many({})

async def get_one_series():
    return await series_catalog.find_one()

# 🔥 NEW: RESET SINGLE MOVIE / SERIES

async def delete_series(title):
    return await series_catalog.delete_one({"_id": title})

# ---------------- USER REQUEST SYSTEM ---------------- #

async def add_request(user_id, name, request):
    await requests_col.insert_one({
        "user_id": user_id,
        "name": name,
        "request": request,
        "status": "pending"
    })

async def approve_request(request_text):
    data = await requests_col.find_one({"request": request_text})
    if not data:
        return None

    await requests_col.update_one(
        {"_id": data["_id"]},
        {"$set": {"status": "approved"}}
    )
    return data

async def get_requests(limit=20):
    return requests_col.find().sort("_id", -1).limit(limit)

async def clear_requests():
    await requests_col.delete_many({})

# ---------------- INLINE SEARCH SUPPORT ---------------- #

async def search_titles(query, limit=20):
    regex = {"$regex": query, "$options": "i"}
    cursor = series_catalog.find({"_id": regex}).limit(limit)
    return await cursor.to_list(length=limit)
