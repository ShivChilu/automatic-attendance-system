from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
from dotenv import load_dotenv
from pathlib import Path
import os
import uuid
import logging
import secrets
import requests

# Load env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection (must use env)
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# App and router with /api prefix
app = FastAPI()
api = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backend")

# Auth settings
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # not used; we accept JSON login

# Email settings (Brevo)
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "School Admin")

# ---------- Models ----------
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

Role = Literal['GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER']

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: Role
    phone: Optional[str] = None
    school_id: Optional[str] = None

class UserCreate(UserBase):
    password: Optional[str] = None  # optional, will auto-generate if not provided
    subject: Optional[str] = None   # for teachers
    section_id: Optional[str] = None  # for teachers

class UserPublic(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: Role
    phone: Optional[str] = None
    school_id: Optional[str] = None
    subject: Optional[str] = None
    section_id: Optional[str] = None
    created_at: datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SchoolCreate(BaseModel):
    name: str
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    principal_name: str
    principal_email: EmailStr
    principal_phone: Optional[str] = None

class School(BaseModel):
    id: str
    name: str
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    principal_name: Optional[str] = None
    principal_email: Optional[EmailStr] = None
    principal_phone: Optional[str] = None
    created_at: datetime

class SectionCreate(BaseModel):
    school_id: str
    name: str
    grade: Optional[str] = None

class Section(BaseModel):
    id: str
    school_id: str
    name: str
    grade: Optional[str] = None
    created_at: datetime

class StudentCreate(BaseModel):
    name: str
    student_code: Optional[str] = None
    roll_no: Optional[str] = None
    section_id: str
    parent_mobile: Optional[str] = None
    has_twin: bool = False
    twin_group_id: Optional[str] = None

class Student(BaseModel):
    id: str
    name: str
    student_code: str
    roll_no: Optional[str] = None
    section_id: str
    parent_mobile: Optional[str] = None
    has_twin: bool
    twin_group_id: Optional[str]
    created_at: datetime

# ---------- Utility functions ----------

def now_iso():
    return datetime.now(timezone.utc)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = now_iso() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGO)

async def get_user_by_email(email: str) -> Optional[dict]:
    return await db.users.find_one({"email": email})

async def brevo_send_credentials(to_email: str, to_name: str, role: str, email: str, temp_password: str) -> Dict[str, Any]:
    """
    Send a simple credentials email via Brevo API. This uses REST to minimize deps.
    Returns a dict with success flag.
    """
    if not BREVO_API_KEY:
        return {"success": False, "error": "BREVO_API_KEY missing"}
    if not BREVO_SENDER_EMAIL:
        return {"success": False, "error": "BREVO_SENDER_EMAIL missing"}

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }
    subject = f"Your {role} account credentials"
    html = f"""
    <h2>Welcome to Automated Attendance System</h2>
    <p>Dear {to_name},</p>
    <p>Your {role} account has been created.</p>
    <ul>
      <li>Email: <b>{email}</b></li>
      <li>Temporary Password: <b>{temp_password}</b></li>
    </ul>
    <p>Please login and change your password immediately.</p>
    """
    data = {
        "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html,
        "textContent": f"Email: {email}\nTemporary Password: {temp_password}\n",
        "tags": ["attendance", "credentials"]
    }
    try:
        resp = requests.post("https://api.brevo.com/v3/smtp/email", headers=headers, json=data, timeout=20)
        if resp.status_code in (200, 201):
            return {"success": True, "messageId": resp.json().get("messageId")}
        else:
            return {"success": False, "error": f"{resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------- Auth dependencies ----------
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise credentials_exception
    return user

def require_roles(*roles: Role):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

# ---------- Routes ----------
@api.get("/")
async def api_root():
    return {"message": "API ok"}

@api.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(client_name=input.client_name)
    await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj

@api.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    items = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**i) for i in items]

# Auth
@api.post("/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    user = await get_user_by_email(data.email)
    if not user or not verify_password(data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user["id"], "role": user["role"], "school_id": user.get("school_id"), "section_id": user.get("section_id")})
    return TokenResponse(access_token=token)

@api.get("/auth/me", response_model=UserPublic)
async def me(current_user: dict = Depends(get_current_user)):
    return UserPublic(
        id=current_user["id"],
        full_name=current_user["full_name"],
        email=current_user["email"],
        role=current_user["role"],
        phone=current_user.get("phone"),
        school_id=current_user.get("school_id"),
        subject=current_user.get("subject"),
        section_id=current_user.get("section_id"),
        created_at=current_user["created_at"],
    )

# Schools
@api.post("/schools", response_model=School)
async def create_school(payload: SchoolCreate, _: dict = Depends(require_roles('GOV_ADMIN'))):
    school_id = str(uuid.uuid4())
    school_doc = {
        "id": school_id,
        "name": payload.name,
        "address_line1": payload.address_line1,
        "city": payload.city,
        "state": payload.state,
        "pincode": payload.pincode,
        "principal_name": payload.principal_name,
        "principal_email": payload.principal_email.lower(),
        "principal_phone": payload.principal_phone,
        "created_at": now_iso(),
    }
    # Create principal as SCHOOL_ADMIN with temp password
    temp_pass = secrets.token_urlsafe(8)
    principal_doc = {
        "id": str(uuid.uuid4()),
        "full_name": payload.principal_name,
        "email": payload.principal_email.lower(),
        "role": 'SCHOOL_ADMIN',
        "phone": payload.principal_phone,
        "school_id": school_id,
        "password_hash": hash_password(temp_pass),
        "created_at": now_iso(),
    }

    # Ensure email uniqueness
    existing = await db.users.find_one({"email": principal_doc["email"]})
    if existing:
        raise HTTPException(status_code=409, detail="Principal email already exists as a user")

    await db.schools.insert_one(school_doc)
    await db.users.insert_one(principal_doc)

    _ = await brevo_send_credentials(principal_doc['email'], principal_doc['full_name'], 'School Admin', principal_doc['email'], temp_pass)

    return School(**school_doc)

@api.get("/schools", response_model=List[School])
async def list_schools(_: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN'))):
    items = await db.schools.find().to_list(1000)
    return [School(**i) for i in items]

@api.get("/schools/my", response_model=School)
async def my_school(current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER'))):
    sid = current.get("school_id")
    if not sid:
        raise HTTPException(status_code=404, detail="No school associated")
    doc = await db.schools.find_one({"id": sid})
    if not doc:
        raise HTTPException(status_code=404, detail="School not found")
    return School(**doc)

# Sections
@api.post("/sections", response_model=Section)
async def create_section(payload: SectionCreate, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'GOV_ADMIN'))):
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN') and payload.school_id != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Cannot create section for another school")
    sec_id = str(uuid.uuid4())
    doc = {"id": sec_id, "school_id": payload.school_id, "name": payload.name, "grade": payload.grade, "created_at": now_iso()}
    await db.sections.insert_one(doc)
    return Section(**doc)

@api.get("/sections", response_model=List[Section])
async def list_sections(school_id: Optional[str] = None, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'GOV_ADMIN', 'TEACHER'))):
    query: Dict[str, Any] = {}
    if school_id:
        query["school_id"] = school_id
    elif current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        query["school_id"] = current.get("school_id")
    elif current["role"] == 'TEACHER' and current.get("school_id"):
        query["school_id"] = current.get("school_id")
    items = await db.sections.find(query).to_list(1000)
    return [Section(**i) for i in items]

# Students
@api.post("/students", response_model=Student)
async def create_student(payload: StudentCreate, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'GOV_ADMIN'))):
    # Validate section belongs to current school if school admin/co-admin
    sec = await db.sections.find_one({"id": payload.section_id})
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN') and sec.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Cannot add student to another school's section")
    sid = str(uuid.uuid4())
    student_code = payload.student_code or payload.roll_no or sid[:8]
    doc = {
        "id": sid,
        "name": payload.name,
        "student_code": student_code,
        "roll_no": payload.roll_no or payload.student_code,
        "section_id": payload.section_id,
        "parent_mobile": payload.parent_mobile,
        "has_twin": payload.has_twin,
        "twin_group_id": payload.twin_group_id,
        "created_at": now_iso(),
    }
    await db.students.insert_one(doc)
    return Student(**doc)

@api.get("/students", response_model=List[Student])
async def list_students(section_id: Optional[str] = None, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'GOV_ADMIN', 'TEACHER'))):
    query: Dict[str, Any] = {}
    if section_id:
        query["section_id"] = section_id
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        school_sections = [s["id"] for s in await db.sections.find({"school_id": current.get("school_id")}).to_list(1000)]
        if section_id and section_id not in school_sections:
            raise HTTPException(status_code=403, detail="Not allowed")
        if not section_id:
            query["section_id"] = {"$in": school_sections}
    if current["role"] == 'TEACHER' and current.get("section_id"):
        query["section_id"] = current.get("section_id")
    items = await db.students.find(query).to_list(1000)
    return [Student(**i) for i in items]

# Users (Teachers, Co-Admins)
ALLOWED_SUBJECTS = ["Math", "Science", "English", "Social", "Telugu", "Hindi", "Other"]

@api.post("/users/teachers", response_model=UserPublic)
async def create_teacher(payload: UserCreate, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'GOV_ADMIN'))):
    if payload.role != 'TEACHER':
        raise HTTPException(status_code=400, detail="role must be TEACHER for this endpoint")
    # Scope
    school_id = payload.school_id or current.get("school_id")
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        school_id = current.get("school_id")
    if not school_id:
        raise HTTPException(status_code=400, detail="school_id required")

    # Validate subject
    if payload.subject and payload.subject not in ALLOWED_SUBJECTS:
        raise HTTPException(status_code=400, detail="Invalid subject")

    # Validate section if provided
    if payload.section_id:
        sec = await db.sections.find_one({"id": payload.section_id})
        if not sec or sec.get("school_id") != school_id:
            raise HTTPException(status_code=400, detail="Invalid section for this school")

    temp_pass = payload.password or secrets.token_urlsafe(8)
    user_doc = {
        "id": str(uuid.uuid4()),
        "full_name": payload.full_name,
        "email": payload.email.lower(),
        "role": 'TEACHER',
        "phone": payload.phone,
        "school_id": school_id,
        "subject": payload.subject,
        "section_id": payload.section_id,
        "password_hash": hash_password(temp_pass),
        "created_at": now_iso(),
    }
    existing = await db.users.find_one({"email": user_doc["email"]})
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    await db.users.insert_one(user_doc)

    email_result = await brevo_send_credentials(payload.email, payload.full_name, 'Teacher', payload.email, temp_pass)
    if not email_result.get("success"):
        logger.warning(f"Brevo send failed: {email_result.get('error')}")

    return UserPublic(
        id=user_doc["id"], full_name=user_doc["full_name"], email=user_doc["email"], role='TEACHER',
        phone=user_doc.get("phone"), school_id=school_id, subject=user_doc.get("subject"), section_id=user_doc.get("section_id"), created_at=user_doc["created_at"]
    )

@api.post("/users/coadmins", response_model=UserPublic)
async def create_coadmin(payload: UserCreate, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'GOV_ADMIN'))):
    if payload.role != 'CO_ADMIN':
        raise HTTPException(status_code=400, detail="role must be CO_ADMIN for this endpoint")
    school_id = payload.school_id or current.get("school_id")
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        school_id = current.get("school_id")
    if not school_id:
        raise HTTPException(status_code=400, detail="school_id required")

    temp_pass = payload.password or secrets.token_urlsafe(8)
    user_doc = {
        "id": str(uuid.uuid4()),
        "full_name": payload.full_name,
        "email": payload.email.lower(),
        "role": 'CO_ADMIN',
        "phone": payload.phone,
        "school_id": school_id,
        "password_hash": hash_password(temp_pass),
        "created_at": now_iso(),
    }
    existing = await db.users.find_one({"email": user_doc["email"]})
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    await db.users.insert_one(user_doc)

    email_result = await brevo_send_credentials(payload.email, payload.full_name, 'Co-Admin', payload.email, temp_pass)
    if not email_result.get("success"):
        logger.warning(f"Brevo send failed: {email_result.get('error')}")

    return UserPublic(
        id=user_doc["id"], full_name=user_doc["full_name"], email=user_doc["email"], role='CO_ADMIN',
        phone=user_doc.get("phone"), school_id=school_id, created_at=user_doc["created_at"]
    )

# List users by role (scoped)
class UsersListResponse(BaseModel):
    users: List[UserPublic]

@api.get("/users", response_model=UsersListResponse)
async def list_users(role: Role, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN'))):
    query: Dict[str, Any] = {"role": role}
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        query["school_id"] = current.get("school_id")
    items = await db.users.find(query).to_list(1000)
    return {"users": [UserPublic(
        id=u["id"], full_name=u["full_name"], email=u["email"], role=u["role"], phone=u.get("phone"),
        school_id=u.get("school_id"), subject=u.get("subject"), section_id=u.get("section_id"), created_at=u["created_at"]
    ) for u in items]}

# Resend credentials (GOV_ADMIN only)
class ResendReq(BaseModel):
    email: EmailStr
    temp_password: Optional[str] = None

@api.post("/users/resend-credentials")
async def resend_credentials(payload: ResendReq, _: dict = Depends(require_roles('GOV_ADMIN'))):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    temp = payload.temp_password or secrets.token_urlsafe(8)
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(temp)}})
    role_human = 'Teacher' if user['role']=='TEACHER' else ('School Admin' if user['role']=='SCHOOL_ADMIN' else 'Co-Admin' if user['role']=='CO_ADMIN' else 'Government Admin')
    send_res = await brevo_send_credentials(user['email'], user['full_name'], role_human, user['email'], temp)
    return {"sent": bool(send_res.get('success')), "email": user['email'], "role": user['role'], "brevo": send_res}

# ---------- Startup tasks: indexes + seeding ----------
@app.on_event("startup")
async def on_startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.schools.create_index("name")
    await db.sections.create_index("school_id")
    await db.students.create_index("section_id")

    # Seed initial users/school if provided in env
    try:
        gov_email = os.getenv("SEED_GOV_ADMIN_EMAIL")
        gov_name = os.getenv("SEED_GOV_ADMIN_NAME") or "Gov Admin"
        gov_pass = os.getenv("SEED_GOV_ADMIN_PASSWORD")
        school_name = os.getenv("SEED_SCHOOL_NAME")
        school_admin_email = os.getenv("SEED_SCHOOL_ADMIN_EMAIL")
        school_admin_name = os.getenv("SEED_SCHOOL_ADMIN_NAME") or "School Admin"
        school_admin_pass = os.getenv("SEED_SCHOOL_ADMIN_PASSWORD")

        # Seed GOV_ADMIN
        if gov_email and not await db.users.find_one({"email": gov_email.lower()}):
            temp = gov_pass or secrets.token_urlsafe(8)
            gov_doc = {
                "id": str(uuid.uuid4()),
                "full_name": gov_name,
                "email": gov_email.lower(),
                "role": 'GOV_ADMIN',
                "phone": None,
                "school_id": None,
                "password_hash": hash_password(temp),
                "created_at": now_iso(),
            }
            await db.users.insert_one(gov_doc)
            _ = await brevo_send_credentials(gov_email, gov_name, 'Government Admin', gov_email, temp)
            logger.info("Seeded Government Admin user")

        # Seed School and School Admin
        school_id = None
        if school_name:
            existing_school = await db.schools.find_one({"name": school_name})
            if existing_school:
                school_id = existing_school["id"]
            else:
                school_id = str(uuid.uuid4())
                await db.schools.insert_one({"id": school_id, "name": school_name, "created_at": now_iso()})
                logger.info(f"Seeded school {school_name}")

        if school_admin_email and school_id and not await db.users.find_one({"email": school_admin_email.lower()}):
            temp2 = school_admin_pass or secrets.token_urlsafe(8)
            sa_doc = {
                "id": str(uuid.uuid4()),
                "full_name": school_admin_name,
                "email": school_admin_email.lower(),
                "role": 'SCHOOL_ADMIN',
                "phone": None,
                "school_id": school_id,
                "password_hash": hash_password(temp2),
                "created_at": now_iso(),
            }
            await db.users.insert_one(sa_doc)
            _ = await brevo_send_credentials(school_admin_email, school_admin_name, 'School Admin', school_admin_email, temp2)
            logger.info("Seeded School Admin user")

        # If GOV_ADMIN exists and password provided, update
        if gov_email and gov_pass:
            existing_gov = await db.users.find_one({"email": gov_email.lower()})
            if existing_gov and existing_gov.get("role") == 'GOV_ADMIN':
                await db.users.update_one({"id": existing_gov["id"]}, {"$set": {"password_hash": hash_password(gov_pass)}})
                logger.info("Updated Government Admin password from seed env")

        if school_admin_email and school_admin_pass:
            existing_sa = await db.users.find_one({"email": school_admin_email.lower()})
            if existing_sa and existing_sa.get("role") == 'SCHOOL_ADMIN':
                await db.users.update_one({"id": existing_sa["id"]}, {"$set": {"password_hash": hash_password(school_admin_pass)}})
                logger.info("Updated School Admin password from seed env")

    except Exception as e:
        logger.error(f"Startup seeding failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Mount router
app.include_router(api)