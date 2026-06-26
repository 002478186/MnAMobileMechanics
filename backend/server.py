from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import asyncio
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import resend


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Resend setup
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
OWNER_EMAIL = os.environ.get('OWNER_EMAIL', 'precisionfix12@gmail.com')

# App
app = FastAPI(title="M&A Precision Mechanical API")
api_router = APIRouter(prefix="/api")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Models =====
class BookingCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)
    phone: str = Field(..., min_length=5, max_length=40)
    email: EmailStr
    service_type: str
    vehicle: str = Field(..., min_length=1, max_length=160)
    preferred_datetime: str  # ISO string from frontend
    issue: str = Field(..., min_length=1, max_length=2000)


class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str
    phone: str
    email: EmailStr
    service_type: str
    vehicle: str
    preferred_datetime: str
    issue: str
    email_sent: bool = False
    email_error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===== Email helpers =====
def _booking_html(b: Booking) -> str:
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, sans-serif; background:#0A0A0A; color:#ffffff; padding:24px;">
      <tr>
        <td>
          <table width="600" cellpadding="0" cellspacing="0" align="center" style="background:#121212; border:1px solid #2A2A2A;">
            <tr>
              <td style="padding:24px; border-bottom:3px solid #E10600;">
                <h1 style="margin:0; color:#ffffff; font-size:22px; letter-spacing:2px;">M&amp;A PRECISION MECHANICAL INC</h1>
                <p style="margin:6px 0 0; color:#E10600; font-size:13px; letter-spacing:3px;">NEW BOOKING REQUEST</p>
              </td>
            </tr>
            <tr>
              <td style="padding:24px;">
                <table width="100%" cellpadding="8" cellspacing="0" style="color:#ffffff; font-size:14px;">
                  <tr><td style="color:#A0A0A0; width:40%;">Full Name</td><td><strong>{b.full_name}</strong></td></tr>
                  <tr><td style="color:#A0A0A0;">Phone</td><td><strong>{b.phone}</strong></td></tr>
                  <tr><td style="color:#A0A0A0;">Email</td><td><strong>{b.email}</strong></td></tr>
                  <tr><td style="color:#A0A0A0;">Service Type</td><td><strong>{b.service_type}</strong></td></tr>
                  <tr><td style="color:#A0A0A0;">Vehicle</td><td><strong>{b.vehicle}</strong></td></tr>
                  <tr><td style="color:#A0A0A0;">Preferred Date/Time</td><td><strong>{b.preferred_datetime}</strong></td></tr>
                  <tr><td style="color:#A0A0A0; vertical-align:top;">Issue</td><td>{b.issue}</td></tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 24px; border-top:1px solid #2A2A2A; color:#A0A0A0; font-size:12px;">
                Booking ID: {b.id} &middot; Submitted: {b.created_at.isoformat()}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """


async def _send_owner_email(b: Booking) -> tuple[bool, Optional[str]]:
    if not resend.api_key:
        return False, "RESEND_API_KEY not configured"
    params = {
        "from": SENDER_EMAIL,
        "to": [OWNER_EMAIL],
        "reply_to": b.email,
        "subject": f"New Booking: {b.service_type} - {b.full_name}",
        "html": _booking_html(b),
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Resend email sent: {result}")
        return True, None
    except Exception as e:
        logger.error(f"Resend send failed: {e}")
        return False, str(e)


# ===== Routes =====
@api_router.get("/")
async def root():
    return {"message": "M&A Precision Mechanical API"}


@api_router.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@api_router.post("/bookings", response_model=Booking)
async def create_booking(payload: BookingCreate):
    # Validate service type
    allowed = {"Inspection", "Diagnostics", "Repair", "Maintenance"}
    if payload.service_type not in allowed:
        raise HTTPException(status_code=400, detail=f"service_type must be one of {sorted(allowed)}")

    booking = Booking(**payload.model_dump())

    # Try to send the email; do not fail the booking if email fails
    sent, err = await _send_owner_email(booking)
    booking.email_sent = sent
    booking.email_error = err

    # Persist
    doc = booking.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.bookings.insert_one(doc)

    return booking


@api_router.get("/bookings", response_model=List[Booking])
async def list_bookings():
    docs = await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for d in docs:
        if isinstance(d.get('created_at'), str):
            try:
                d['created_at'] = datetime.fromisoformat(d['created_at'])
            except Exception:
                d['created_at'] = datetime.now(timezone.utc)
    return docs


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
