import os
# Fix MediaPipe protobuf issues in container environment
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form
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

# Make validation errors user-friendly (avoid [object Object] in frontend alerts)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    try:
        errs = []
        for e in exc.errors():
            loc = ".".join([str(x) for x in e.get("loc", [])])
            msg = e.get("msg", "validation error")
            errs.append(f"{loc}: {msg}")
        message = "; ".join(errs) if errs else "Invalid request payload"
    except Exception:
        message = "Invalid request payload"
    return JSONResponse(status_code=422, content={"detail": message})

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check root endpoint to satisfy platform monitors
@app.get("/")
async def root_health():
    return {"ok": True, "service": "attendance-backend", "status": "healthy"}


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
    section_ids: Optional[List[str]] = None
    all_sections: Optional[bool] = False
    created_at: datetime

# Endpoint-specific request models (avoid requiring 'role' in body)
class TeacherCreateRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: Optional[str] = None
    section_id: Optional[str] = None  # legacy single section
    section_ids: Optional[List[str]] = None  # new multi-section
    all_sections: Optional[bool] = False  # grant access to all sections of school
    password: Optional[str] = None
    school_id: Optional[str] = None  # only for GOV_ADMIN usage

class CoadminCreateRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: Optional[str] = None
    school_id: Optional[str] = None  # only for GOV_ADMIN usage

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

class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    principal_name: Optional[str] = None
    principal_email: Optional[EmailStr] = None
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

class SectionUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None

class Section(BaseModel):
    id: str
    school_id: str
    name: str
    grade: Optional[str] = None
    created_at: datetime

class StudentCreate(BaseModel):
    name: str
    gender: Optional[Literal['Male','Female','Other']] = None
    student_code: Optional[str] = None
    roll_no: Optional[str] = None
    section_id: str
    parent_mobile: Optional[str] = None
    has_twin: bool = False
    twin_group_id: Optional[str] = None
    twin_of: Optional[str] = None  # link to sibling student id

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[Literal['Male','Female','Other']] = None
    student_code: Optional[str] = None
    roll_no: Optional[str] = None
    parent_mobile: Optional[str] = None

class Student(BaseModel):
    id: str
    name: str
    gender: Optional[Literal['Male','Female','Other']] = None
    student_code: str = ""
    roll_no: Optional[str] = None
    section_id: str
    parent_mobile: Optional[str] = None
    has_twin: bool = False
    twin_group_id: Optional[str] = None
    twin_of: Optional[str] = None
    created_at: datetime

# ---------- Utility functions ----------
# ---------- Face utilities (MediaPipe Face Mesh + MobileFaceNet TFLite) ----------
FACE_MESH = None  # MediaPipe Face Mesh initialized on first use
MOBILEFACENET_MODEL = None  # TFLite model initialized on first use

async def _ensure_face_mesh():
    global FACE_MESH
    if FACE_MESH is None:
        try:
            # Clear any existing MediaPipe imports to avoid conflicts
            import sys
            mediapipe_modules = [module for module in sys.modules.keys() if 'mediapipe' in module]
            for module in mediapipe_modules:
                if module in sys.modules:
                    del sys.modules[module]
            import mediapipe as mp  # type: ignore
            FACE_MESH = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=False,
                min_detection_confidence=0.3,
                min_tracking_confidence=0.3
            )
            logger.info("MediaPipe Face Mesh initialized successfully")
        except Exception as e:
            logger.warning(f"MediaPipe Face Mesh not available or failed to initialize: {e}")
            try:
                import mediapipe as mp
                FACE_MESH = mp.solutions.face_mesh.FaceMesh(
                    static_image_mode=True,
                    max_num_faces=1,
                    min_detection_confidence=0.3
                )
                logger.info("MediaPipe Face Mesh initialized with minimal config")
            except Exception as e2:
                logger.error(f"MediaPipe Face Mesh completely failed to initialize: {e2}")
                FACE_MESH = None
    return FACE_MESH

async def _detect_and_crop_face_mesh(image_bytes: bytes):
    try:
        import numpy as np
        import cv2  # type: ignore
        from PIL import Image
    except Exception as e:
        return None, "face_mesh_not_available"
    fm = await _ensure_face_mesh()
    if fm is None:
        return None, "face_mesh_not_available"
    import io
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    arr = np.array(img)
    h, w = arr.shape[:2]
    try:
        import mediapipe as mp  # type: ignore
    except Exception:
        return None, "face_mesh_not_available"
    rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    res = fm.process(rgb)
    if not res.multi_face_landmarks:
        return None, "no_face"
    x_min, y_min, x_max, y_max = w, h, 0, 0
    for lm in res.multi_face_landmarks[0].landmark:
        x = int(lm.x * w)
        y = int(lm.y * h)
        x_min = min(x_min, x)
        y_min = min(y_min, y)
        x_max = max(x_max, x)
        y_max = max(y_max, y)
    pad = 20
    x0 = max(0, x_min - pad)
    y0 = max(0, y_min - pad)
    x1 = min(w, x_max + pad)
    y1 = min(h, y_max + pad)
    face = arr[y0:y1, x0:x1]
    if face.size == 0:
        return None, "crop_failed"
    return face, None

async def _ensure_mobilefacenet_model():
    global MOBILEFACENET_MODEL
    if MOBILEFACENET_MODEL is None:
        try:
            import tflite_runtime.interpreter as tflite
            model_path = ROOT_DIR / 'models' / 'mobilefacenet.tflite'
            MOBILEFACENET_MODEL = tflite.Interpreter(model_path=str(model_path))
            MOBILEFACENET_MODEL.allocate_tensors()
            logger.info("MobileFaceNet TFLite model loaded successfully")
        except Exception as e:
            logger.warning(f"MobileFaceNet TFLite model not available or failed to initialize: {e}")
            MOBILEFACENET_MODEL = None
    return MOBILEFACENET_MODEL

async def _embed_face_with_mobilefacenet(face_bgr):
    try:
        import numpy as np
        import cv2  # type: ignore
    except Exception:
        return None, "mobilefacenet_not_available"
    inter = await _ensure_mobilefacenet_model()
    if inter is None:
        return None, "mobilefacenet_not_available"
    try:
        import numpy as np
        face = cv2.resize(face_bgr, (112, 112))
        face = (face.astype(np.float32) - 127.5) / 128.0
        face = np.expand_dims(face, axis=0)
        input_details = inter.get_input_details()[0]
        output_details = inter.get_output_details()[0]
        inter.set_tensor(input_details['index'], face)
        inter.invoke()
        emb = inter.get_tensor(output_details['index'])[0]
        # L2 normalize
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        emb = emb.tolist()
        return emb, None
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None, "embed_failed"

def _cosine_sim(a: List[float], b: List[float]) -> float:
    try:
        import numpy as np
        aa = np.array(a); bb = np.array(b)
        if aa.size == 0 or bb.size == 0:
            return -1.0
        num = (aa * bb).sum()
        den = ( (aa**2).sum() ** 0.5 ) * ( (bb**2).sum() ** 0.5 )
        if den == 0:
            return -1.0
        return float(num / den)
    except Exception:
        return -1.0

# ---------- Helpers ----------

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
    return {"message": "API ok", "debug": "root route working"}

@api.post("/status", response_model=StatusCheck)

# Lightweight test endpoint for external health probes
@api.get("/test-route")
async def api_test_route():
    return {"ok": True, "path": "/api/test-route"}


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
        section_ids=current_user.get("section_ids"),
        all_sections=bool(current_user.get("all_sections", False)),
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
    existing = await db.users.find_one({"email": principal_doc["email"]})
    if existing:
        raise HTTPException(status_code=409, detail="Principal email already exists as a user")
    await db.schools.insert_one(school_doc)
    await db.users.insert_one(principal_doc)
    _ = await brevo_send_credentials(principal_doc['email'], principal_doc['full_name'], 'School Admin', principal_doc['email'], temp_pass)
    return School(**school_doc)

@api.put("/schools/{school_id}", response_model=School)
async def update_school(school_id: str, payload: SchoolUpdate, _: dict = Depends(require_roles('GOV_ADMIN'))):
    upd = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not upd:
        raise HTTPException(status_code=400, detail="Nothing to update")
    if 'principal_email' in upd:
        upd['principal_email'] = upd['principal_email'].lower()
    await db.schools.find_one_and_update({"id": school_id}, {"$set": upd}, return_document=True)
    doc = await db.schools.find_one({"id": school_id})
    if not doc:
        raise HTTPException(status_code=404, detail="School not found")
    return School(**doc)

@api.delete("/schools/{school_id}")
async def delete_school(school_id: str, _: dict = Depends(require_roles('GOV_ADMIN'))):
    school = await db.schools.find_one({"id": school_id})
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    sections = await db.sections.find({"school_id": school_id}).to_list(10000)
    section_ids = [s['id'] for s in sections]
    if section_ids:
        await db.students.delete_many({"section_id": {"$in": section_ids}})
        await db.sections.delete_many({"id": {"$in": section_ids}})
    await db.users.delete_many({"school_id": school_id})
    await db.schools.delete_one({"id": school_id})
    return {"deleted": True}

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

@api.put("/sections/{section_id}", response_model=Section)
async def update_section(section_id: str, payload: SectionUpdate, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'GOV_ADMIN'))):
    sec = await db.sections.find_one({"id": section_id})
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
    if current['role'] == 'SCHOOL_ADMIN' and sec.get('school_id') != current.get('school_id'):
        raise HTTPException(status_code=403, detail="Not allowed")
    upd = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not upd:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await db.sections.update_one({"id": section_id}, {"$set": upd})
    updated_sec = await db.sections.find_one({"id": section_id})
    return Section(**updated_sec)

# ---------- Student Face Enrollment & Attendance ----------
# Announcements models
class AnnouncementCreate(BaseModel):
    title: str
    description: str
    target_all: bool = False
    target_teacher_ids: Optional[List[str]] = None  # if not target_all

class AnnouncementPublic(BaseModel):
    id: str
    school_id: str
    created_by: str
    title: str
    description: str
    target_all: bool
    target_teacher_ids: List[str] = []
    created_at: datetime


# ---------- Announcements Endpoints ----------
class AnnouncementsList(BaseModel):
    items: List[AnnouncementPublic]

@api.post("/announcements", response_model=AnnouncementPublic)
async def create_announcement(payload: AnnouncementCreate, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN'))):
    school_id = current.get("school_id")
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with admin")
    target_ids: List[str] = []
    if not payload.target_all:
        if not payload.target_teacher_ids or not isinstance(payload.target_teacher_ids, list):
            raise HTTPException(status_code=400, detail="Please choose at least one teacher or select All")
        # Validate teachers belong to the same school
        teacher_docs = await db.users.find({
            "id": {"$in": payload.target_teacher_ids},
            "role": "TEACHER",
            "school_id": school_id,
        }).to_list(10000)
        valid = {t['id'] for t in teacher_docs}
        if len(valid) != len(payload.target_teacher_ids):
            raise HTTPException(status_code=400, detail="One or more selected teachers are invalid")
        target_ids = list(valid)
    ann_id = str(uuid.uuid4())
    doc = {
        "id": ann_id,
        "school_id": school_id,
        "created_by": current.get("id"),
        "title": payload.title,
        "description": payload.description,
        "target_all": bool(payload.target_all),
        "target_teacher_ids": target_ids,
        "created_at": now_iso(),
    }
    await db.announcements.insert_one(doc)
    return AnnouncementPublic(**doc)

@api.get("/announcements", response_model=AnnouncementsList)
async def list_announcements(school_id: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER'))):
    q: Dict[str, Any] = {}
    if current['role'] == 'TEACHER':
        if not current.get('school_id'):
            return {"items": []}
        q = {
            "school_id": current.get('school_id'),
            "$or": [
                {"target_all": True},
                {"target_teacher_ids": current.get('id')},
            ]
        }
    elif current['role'] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        q = {"school_id": current.get('school_id')}
    else:  # GOV_ADMIN
        if school_id:
            q = {"school_id": school_id}
        else:
            q = {}
    items = await db.announcements.find(q).sort("created_at", -1).limit(200).to_list(500)
    return {"items": [AnnouncementPublic(**i) for i in items]}

# List students
@api.get("/students", response_model=List[Student])
async def list_students(
    section_id: Optional[str] = None,
    enrolled_only: Optional[bool] = False,
    current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER')),
):
    query: Dict[str, Any] = {}
    if section_id:
        query["section_id"] = section_id
    if current['role'] in ('SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER') and current.get('school_id'):
        school_sections = await db.sections.find({"school_id": current.get('school_id')}).to_list(10000)
        allowed_sec_ids = {s['id'] for s in school_sections}
        if section_id and section_id not in allowed_sec_ids:
            raise HTTPException(status_code=403, detail="Not allowed for this section")
        if not section_id:
            query["section_id"] = {"$in": list(allowed_sec_ids)}
    if enrolled_only:
        query["embeddings.0"] = {"$exists": True}
    items = await db.students.find(query).to_list(10000)
    try:
        logger.info(f"GET /api/students -> query={query} count={len(items)}")
    except Exception:
        pass
    def normalize_student(d: Dict[str, Any]) -> Dict[str, Any]:
        sid = str(d.get("id", ""))
        name = str(d.get("name", ""))
        student_code = d.get("student_code") or d.get("roll_no") or (sid[:8] if sid else "")
        roll_no = d.get("roll_no")
        if roll_no is not None:
            roll_no = str(roll_no)
        section_id = str(d.get("section_id", ""))
        parent_mobile = d.get("parent_mobile")
        if parent_mobile is not None:
            parent_mobile = str(parent_mobile)
        has_twin_val = d.get("has_twin", False)
        has_twin_val = bool(has_twin_val) if isinstance(has_twin_val, (bool, int)) else str(has_twin_val).lower() in ("1", "true", "yes")
        twin_group_id = d.get("twin_group_id")
        if twin_group_id is not None:
            twin_group_id = str(twin_group_id)
        twin_of = d.get("twin_of")
        if twin_of is not None:
            twin_of = str(twin_of)
        created = d.get("created_at")
        if not isinstance(created, datetime):
            try:
                if isinstance(created, str) and len(created) > 0:
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                else:
                    created = now_iso()
            except Exception:
                created = now_iso()
        return {
            "id": sid,
            "name": name,
            "gender": (d.get("gender") if d.get("gender") in ("Male","Female","Other") else None),
            "student_code": str(student_code or ""),
            "roll_no": roll_no,
            "section_id": section_id,
            "parent_mobile": parent_mobile,
            "has_twin": bool(has_twin_val),
            "twin_group_id": twin_group_id,
            "twin_of": twin_of,
            "created_at": created,
        }
    normalized = [normalize_student(i) for i in items]
    result: List[Student] = []
    for n in normalized:
        try:
            n["student_code"] = str(n.get("student_code") or "")
            n["has_twin"] = bool(n.get("has_twin", False))
            n["twin_group_id"] = n.get("twin_group_id") or None
            n["twin_of"] = n.get("twin_of") or None
            result.append(Student(**n))
        except Exception as e:
            logger.error(f"Skipping malformed student doc id={n.get('id')} error={e}")
            continue
    return result

# Search students
class StudentSearchItem(BaseModel):
    id: str
    name: str
    section_id: str
    roll_no: Optional[str] = None
    student_code: Optional[str] = None

class StudentSearchResponse(BaseModel):
    items: List[StudentSearchItem]

@api.get("/students/search", response_model=StudentSearchResponse)
async def search_students(query: str, section_id: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER'))):
    flt: Dict[str, Any] = {
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"roll_no": {"$regex": query, "$options": "i"}},
            {"student_code": {"$regex": query, "$options": "i"}},
        ]
    }
    if section_id:
        flt["section_id"] = section_id
    else:
        if current.get("role") in ("SCHOOL_ADMIN", "CO_ADMIN", "TEACHER") and current.get("school_id"):
            secs = await db.sections.find({"school_id": current.get("school_id")}).to_list(10000)
            allowed = [s["id"] for s in secs]
            flt["section_id"] = {"$in": allowed}
    docs = await db.students.find(flt).limit(25).to_list(100)
    items = [StudentSearchItem(id=d["id"], name=d["name"], section_id=d["section_id"], roll_no=d.get("roll_no"), student_code=d.get("student_code")) for d in docs]
    return {"items": items}

# Enrollment
class StudentEnrollResponse(BaseModel):
    id: str
    name: str
    section_id: str
    parent_mobile: Optional[str] = None
    embeddings_count: int
    has_twin: bool
    twin_of: Optional[str] = None

@api.post("/enrollment/students", response_model=StudentEnrollResponse)
async def enroll_student(
    name: str = Form(...),
    section_id: str = Form(...),
    parent_mobile: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    has_twin: bool = Form(False),
    twin_group_id: Optional[str] = Form(None),
    twin_of: Optional[str] = Form(None),
    images: List[UploadFile] = File(...),
    current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN')),
):
    logger.info("Face enrollment endpoint called successfully!")
    sec = await db.sections.find_one({"id": section_id})
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN') and sec.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Not your school section")
    embeddings: List[List[float]] = []
    for f in images[:5]:
        data = await f.read()
        face, err = await _detect_and_crop_face_mesh(data)
        if face is None:
            logger.warning(f"Face detection failed for image: {err}")
            continue
        emb, e2 = await _embed_face_with_mobilefacenet(face)
        if emb:
            embeddings.append(emb)
        else:
            logger.warning(f"Face embedding failed: {e2}")
    if len(embeddings) < 1:
        raise HTTPException(status_code=400, detail="No face embeddings could be extracted")
    sid = str(uuid.uuid4())
    student_code = sid[:8]
    if twin_of:
        other = await db.students.find_one({"id": twin_of})
        if not other:
            raise HTTPException(status_code=404, detail="Provided twin_of student not found")
        if other.get("section_id") != section_id:
            raise HTTPException(status_code=400, detail="Twin must be in the same section")
        has_twin = True
        if not twin_group_id:
            twin_group_id = other.get("twin_group_id") or other.get("id")
    doc = {
        "id": sid,
        "name": name,
        "gender": (gender if gender in ['Male','Female','Other'] else None),
        "student_code": student_code,
        "roll_no": None,
        "section_id": section_id,
        "parent_mobile": parent_mobile,
        "has_twin": bool(has_twin),
        "twin_group_id": twin_group_id,
        "twin_of": twin_of,
        "embeddings": embeddings,
        "created_at": now_iso(),
    }
    await db.students.insert_one(doc)
    if twin_of and other and not other.get("twin_of"):
        await db.students.update_one({"id": twin_of}, {"$set": {"twin_of": sid, "has_twin": True, "twin_group_id": doc["twin_group_id"]}})
    return StudentEnrollResponse(id=sid, name=name, section_id=section_id, parent_mobile=parent_mobile, embeddings_count=len(embeddings), has_twin=bool(has_twin), twin_of=twin_of)

# Preflight
@api.options("/enrollment/students")
async def options_students_enroll():
    return {"ok": True}

@api.options("/attendance/mark")
async def options_attendance_mark():
    return {"ok": True}

# Attendance scanning and summary
class AttendanceMarkResponse(BaseModel):
    status: str
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    similarity: Optional[float] = None
    twin_conflict: bool = False
    twin_candidates: Optional[List[Dict[str, str]]] = None

# New: Attendance sessions models
class AttendanceSessionCreate(BaseModel):
    section_id: str
    date: Optional[str] = None
    start_time: str
    end_time: str

class AttendanceSessionPublic(BaseModel):
    id: str
    section_id: str
    teacher_id: str
    date: str
    start_time: str
    end_time: str
    duration_minutes: int
    locked: bool
    created_at: datetime
    submitted_at: Optional[datetime] = None

class SessionStudentItem(BaseModel):
    student_id: str
    name: str
    status: Literal['Not Marked','Present','Absent']
    marked_at: Optional[str] = None

class AttendanceSessionDetail(BaseModel):
    session: AttendanceSessionPublic
    students: List[SessionStudentItem]

# Helpers for time validation
_DEF_STEP = 15

def _parse_hhmm(t: str) -> Optional[int]:
    try:
        hh, mm = t.split(":")
        h = int(hh); m = int(mm)
        if h < 0 or h > 23 or m not in (0, 15, 30, 45):
            return None
        return h * 60 + m
    except Exception:
        return None

# Create session
@api.post("/attendance/sessions", response_model=AttendanceSessionPublic)
async def create_session(payload: AttendanceSessionCreate, current: dict = Depends(require_roles('TEACHER'))):
    # Determine allowed sections for this teacher
    allowed: List[str] = []
    if current.get("all_sections"):
        # all sections in this school
        secs = await db.sections.find({"school_id": current.get("school_id")}).to_list(10000)
        allowed = [s['id'] for s in secs]
    else:
        if current.get("section_ids"):
            allowed = list(current.get("section_ids") or [])
        elif current.get("section_id"):
            allowed = [current.get("section_id")]
    if not allowed:
        raise HTTPException(status_code=400, detail="Teacher has no section allotment. Please contact admin.")
    if payload.section_id not in allowed:
        raise HTTPException(status_code=403, detail="Select a section allotted to you")
    # Date validation: must be today
    today = datetime.now(timezone.utc).date()
    date_str = payload.date or today.isoformat()
    if date_str != today.isoformat():
        raise HTTPException(status_code=400, detail="Date must be today")
    # Time validation
    s = _parse_hhmm(payload.start_time)
    e = _parse_hhmm(payload.end_time)
    if s is None or e is None or e <= s:
        raise HTTPException(status_code=400, detail="Invalid time selection")
    duration = e - s
    if duration < 45 or duration > 120:
        raise HTTPException(status_code=400, detail="Class duration must be between 45 mins and 2 hours")
    # Create
    sid = str(uuid.uuid4())
    doc = {
        "id": sid,
        "section_id": payload.section_id,
        "teacher_id": current["id"],
        "date": date_str,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "duration_minutes": duration,
        "locked": False,
        "created_at": now_iso(),
        "submitted_at": None,
    }
    await db.attendance_sessions.insert_one(doc)
    return AttendanceSessionPublic(**doc)

# Get session detail with per-student statuses
@api.get("/attendance/sessions/{session_id}", response_model=AttendanceSessionDetail)
async def get_session(session_id: str, current: dict = Depends(require_roles('TEACHER'))):
    ses = await db.attendance_sessions.find_one({"id": session_id})
    if not ses:
        raise HTTPException(status_code=404, detail="Session not found")
    if ses.get("teacher_id") != current.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")
    # Build student list
    students = await db.students.find({"section_id": ses["section_id"]}).to_list(5000)
    atts = await db.attendance.find({
        "section_id": ses["section_id"],
        "date": ses["date"],
    }).to_list(10000)
    by_id: Dict[str, Dict[str, Any]] = {a['student_id']: a for a in atts}
    items: List[SessionStudentItem] = []
    for s in students:
        a = by_id.get(s['id'])
        if a:
            status = a.get('status', 'Present')
            items.append(SessionStudentItem(student_id=s['id'], name=s['name'], status='Present' if status=='Present' else 'Absent', marked_at=(a.get('timestamp').isoformat() if isinstance(a.get('timestamp'), datetime) else None)))
        else:
            items.append(SessionStudentItem(student_id=s['id'], name=s['name'], status='Not Marked', marked_at=None))
    return AttendanceSessionDetail(session=AttendanceSessionPublic(**ses), students=items)

# List my sessions by date (default today)
@api.get("/attendance/sessions", response_model=List[AttendanceSessionPublic])
async def list_my_sessions(date: Optional[str] = None, current: dict = Depends(require_roles('TEACHER'))):
    today = datetime.now(timezone.utc).date().isoformat()
    d = date or today
    items = await db.attendance_sessions.find({"teacher_id": current["id"], "date": d}).sort("created_at", -1).to_list(100)
    return [AttendanceSessionPublic(**i) for i in items]

# Manual mark present/absent
class ManualMarkRequest(BaseModel):
    session_id: str
    student_id: str
    status: Literal['Present','Absent']

@api.post("/attendance/manual-mark")
async def manual_mark(req: ManualMarkRequest, current: dict = Depends(require_roles('TEACHER'))):
    ses = await db.attendance_sessions.find_one({"id": req.session_id})
    if not ses:
        raise HTTPException(status_code=404, detail="Session not found")
    if ses.get("teacher_id") != current.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")
    if ses.get("locked"):
        raise HTTPException(status_code=400, detail="Session is locked")
    stu = await db.students.find_one({"id": req.student_id, "section_id": ses["section_id"]})
    if not stu:
        raise HTTPException(status_code=404, detail="Student not in this section")
    # Upsert attendance record for that date+student
    await db.attendance.update_one(
        {"section_id": ses["section_id"], "date": ses["date"], "student_id": req.student_id},
        {"$set": {
            "id": str(uuid.uuid4()),
            "section_id": ses["section_id"],
            "student_id": req.student_id,
            "date": ses["date"],
            "status": req.status,
            "teacher_id": current["id"],
            "timestamp": now_iso(),
            "session_id": req.session_id,
        }},
        upsert=True,
    )
    return {"ok": True}

# Submit/lock session
@api.post("/attendance/sessions/{session_id}/submit")
async def submit_session(session_id: str, current: dict = Depends(require_roles('TEACHER'))):
    ses = await db.attendance_sessions.find_one({"id": session_id})
    if not ses:
        raise HTTPException(status_code=404, detail="Session not found")
    if ses.get("teacher_id") != current.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")
    if ses.get("locked"):
        return {"locked": True}
    await db.attendance_sessions.update_one({"id": session_id}, {"$set": {"locked": True, "submitted_at": now_iso()}})
    return {"locked": True}

@api.post("/attendance/mark", response_model=AttendanceMarkResponse)
async def mark_attendance(
    image: UploadFile = File(...),
    section_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    confirmed_student_id: Optional[str] = Form(None),
    current: dict = Depends(require_roles('TEACHER')),
):
    # Determine section within allowed allotment
    allowed: List[str] = []
    if current.get("all_sections"):
        secs = await db.sections.find({"school_id": current.get("school_id")}).to_list(10000)
        allowed = [s['id'] for s in secs]
    else:
        if current.get("section_ids"):
            allowed = list(current.get("section_ids") or [])
        elif current.get("section_id"):
            allowed = [current.get("section_id")]
    if not allowed:
        raise HTTPException(status_code=400, detail="Teacher has no section allotment. Please contact admin.")
    chosen_section = section_id or (allowed[0] if allowed else None)
    if not chosen_section or chosen_section not in allowed:
        raise HTTPException(status_code=403, detail="Not allowed for this section")
    # Validate session if provided
    if session_id:
        ses = await db.attendance_sessions.find_one({"id": session_id})
        if not ses:
            raise HTTPException(status_code=404, detail="Session not found")
        if ses.get("teacher_id") != current.get("id"):
            raise HTTPException(status_code=403, detail="Not allowed")
        if ses.get("locked"):
            raise HTTPException(status_code=400, detail="Session is locked")
        if ses.get("section_id") != chosen_section:
            raise HTTPException(status_code=400, detail="Session-section mismatch")
        # Ensure date is today
        today = datetime.now(timezone.utc).date().isoformat()
        if ses.get("date") != today:
            raise HTTPException(status_code=400, detail="Session date is not today")
    # Section validation
    sec = await db.sections.find_one({"id": chosen_section})
    if not sec or sec.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Invalid section for this teacher")

    if confirmed_student_id:
        stu = await db.students.find_one({"id": confirmed_student_id, "section_id": chosen_section})
        if not stu:
            raise HTTPException(status_code=400, detail="Confirmed student not found in section")
        today = datetime.now(timezone.utc).date()
        start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        existing = await db.attendance.find_one({"student_id": confirmed_student_id, "section_id": chosen_section, "timestamp": {"$gte": start, "$lt": end}})
        if existing:
            if session_id and existing.get('status') == 'Absent':
                await db.attendance.update_one({"student_id": confirmed_student_id, "section_id": chosen_section, "date": start.date().isoformat()}, {"$set": {"status": "Present", "teacher_id": current["id"], "timestamp": now_iso(), "session_id": session_id}})
                return AttendanceMarkResponse(status=f"{stu['name']} is marked present, scan next student", student_id=confirmed_student_id, student_name=stu["name"], similarity=None, twin_conflict=False)
            return AttendanceMarkResponse(status="Already marked present", student_id=confirmed_student_id, student_name=stu["name"], similarity=None, twin_conflict=False)
        rec = {
            "id": str(uuid.uuid4()),
            "date": start.date().isoformat(),
            "section_id": chosen_section,
            "student_id": confirmed_student_id,
            "status": "Present",
            "teacher_id": current["id"],
            "timestamp": now_iso(),
            **({"session_id": session_id} if session_id else {}),
        }
        await db.attendance.insert_one(rec)
        return AttendanceMarkResponse(status=f"{stu['name']} is marked present, scan next student", student_id=confirmed_student_id, student_name=stu["name"], similarity=None, twin_conflict=False)

    data = await image.read()
    face, err = await _detect_and_crop_face_mesh(data)
    if face is None:
        raise HTTPException(status_code=400, detail=f"No face detected: {err}")
    emb, e2 = await _embed_face_with_mobilefacenet(face)
    if not emb:
        raise HTTPException(status_code=400, detail=f"No embedding generated: {e2}")

    students = await db.students.find({"section_id": chosen_section}).to_list(2000)
    best_id = None
    best_name = None
    best_sim = -1.0

    for s in students:
        s_embs = s.get("embeddings", [])
        sims = [_cosine_sim(emb, e) for e in s_embs if isinstance(e, list)]
        sim = max(sims) if sims else -1.0
        if sim > best_sim:
            best_sim = sim
            best_id = s["id"]
            best_name = s["name"]

    threshold = 0.90
    if best_sim < threshold:
        return AttendanceMarkResponse(status="Not a student from this section")

    stu = await db.students.find_one({"id": best_id})
    if stu and stu.get("has_twin") and stu.get("twin_group_id"):
        today = datetime.now(timezone.utc).date()
        start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        present_ids = set()
        cur = db.attendance.find({
            "section_id": chosen_section,
            "timestamp": {"$gte": start, "$lt": end},
            "status": "Present"
        })
        async for a in cur:
            present_ids.add(a["student_id"])
        twins = await db.students.find({"section_id": chosen_section, "twin_group_id": stu["twin_group_id"]}).to_list(10)
        unmarked_twins = [t for t in twins if t["id"] not in present_ids]
        if len(unmarked_twins) == 1:
            best_id = unmarked_twins[0]["id"]
            best_name = unmarked_twins[0]["name"]
        elif len(unmarked_twins) >= 2:
            candidates = [{"id": t["id"], "name": t["name"]} for t in twins]
            return AttendanceMarkResponse(status="Twin detected. Please confirm who it is.", twin_conflict=True, twin_candidates=candidates)

    today = datetime.now(timezone.utc).date()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    existing = await db.attendance.find_one({"student_id": best_id, "section_id": chosen_section, "timestamp": {"$gte": start, "$lt": end}})
    if existing:
        if session_id and existing.get('status') == 'Absent':
            await db.attendance.update_one({"student_id": best_id, "section_id": chosen_section, "date": start.date().isoformat()}, {"$set": {"status": "Present", "teacher_id": current["id"], "timestamp": now_iso(), "session_id": session_id}})
            return AttendanceMarkResponse(status=f"{best_name} is marked present, scan next student", student_id=best_id, student_name=best_name, similarity=best_sim, twin_conflict=False)
        return AttendanceMarkResponse(status="Already marked present", student_id=best_id, student_name=best_name, similarity=best_sim, twin_conflict=False)

    rec = {
        "id": str(uuid.uuid4()),
        "date": start.date().isoformat(),
        "section_id": chosen_section,
        "student_id": best_id,
        "status": "Present",
        "teacher_id": current["id"],
        "timestamp": now_iso(),
        **({"session_id": session_id} if session_id else {}),
    }
    await db.attendance.insert_one(rec)
    return AttendanceMarkResponse(status=f"{best_name} is marked present, scan next student", student_id=best_id, student_name=best_name, similarity=best_sim, twin_conflict=False)

# Attendance summary
class AttendanceSummaryItem(BaseModel):
    student_id: str
    name: str
    present: bool
    marked_at: Optional[str] = None

class AttendanceSummary(BaseModel):
    section_id: str
    date: str
    total: int
    present_count: int
    items: List[AttendanceSummaryItem]

@api.get("/attendance/summary", response_model=AttendanceSummary)
async def attendance_summary(section_id: str, date: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER'))):
    sec = await db.sections.find_one({"id": section_id})
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
    if current['role'] in ('SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER') and sec.get('school_id') != current.get('school_id'):
        raise HTTPException(status_code=403, detail="Not allowed")
    if date is None:
        today = datetime.now(timezone.utc).date()
        date = today.isoformat()
    students = await db.students.find({"section_id": section_id}).to_list(5000)
    atts = await db.attendance.find({"section_id": section_id, "date": date}).to_list(10000)
    present_ids = {a['student_id'] for a in atts if a.get('status') == 'Present'}
    time_by_id = {a['student_id']: (a.get('timestamp').isoformat() if isinstance(a.get('timestamp'), datetime) else None) for a in atts if a.get('status') == 'Present'}
    items = [AttendanceSummaryItem(student_id=s['id'], name=s['name'], present=s['id'] in present_ids, marked_at=time_by_id.get(s['id'])) for s in students]
    return AttendanceSummary(section_id=section_id, date=date, total=len(students), present_count=len(present_ids), items=items)


# ---------- Daily Analytics Endpoints ----------
class SectionDailyItem(BaseModel):
    section_id: str
    name: str
    total_students: int
    present_count: int
    percent: float

class SectionDailyResponse(BaseModel):
    date: str
    items: List[SectionDailyItem]
    total_sections: int
    total_students: int
    total_present: int

@api.get("/attendance/sections/daily", response_model=SectionDailyResponse)
async def sections_daily(date: Optional[str] = None, school_id: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN'))):
    day = (date or datetime.now(timezone.utc).date().isoformat())
    # Resolve school scope
    target_school_id = None
    if current['role'] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        target_school_id = current.get('school_id')
    elif current['role'] == 'GOV_ADMIN':
        target_school_id = school_id
    # Load sections in scope
    sec_query: Dict[str, Any] = {}
    if target_school_id:
        sec_query['school_id'] = target_school_id
    sections = await db.sections.find(sec_query).to_list(10000)
    sec_ids = [s['id'] for s in sections]
    if not sec_ids:
        return SectionDailyResponse(date=day, items=[], total_sections=0, total_students=0, total_present=0)
    # Students per section
    st_agg = db.students.aggregate([
        {"$match": {"section_id": {"$in": sec_ids}}},
        {"$group": {"_id": "$section_id", "total": {"$sum": 1}}}
    ])
    students_map: Dict[str, int] = {}
    async for g in st_agg:
        students_map[g['_id']] = int(g['total'])
    # Present per section on day
    att_agg = db.attendance.aggregate([
        {"$match": {"section_id": {"$in": sec_ids}, "date": day, "status": "Present"}},
        {"$group": {"_id": "$section_id", "present": {"$sum": 1}}}
    ])
    present_map: Dict[str, int] = {}
    async for g in att_agg:
        present_map[g['_id']] = int(g['present'])
    items: List[SectionDailyItem] = []
    total_students = 0
    total_present = 0
    for s in sections:
        tot = int(students_map.get(s['id'], 0))
        pres = int(present_map.get(s['id'], 0))
        pct = float(round((pres / tot) * 100, 2)) if tot > 0 else 0.0
        items.append(SectionDailyItem(section_id=s['id'], name=(s.get('name') or 'Section'), total_students=tot, present_count=pres, percent=pct))
        total_students += tot
        total_present += pres
    return SectionDailyResponse(date=day, items=items, total_sections=len(items), total_students=total_students, total_present=total_present)

class TeacherDailyItem(BaseModel):
    teacher_id: str
    name: str
    email: Optional[EmailStr] = None
    section_id: Optional[str] = None
    section_name: Optional[str] = None
    total_students: Optional[int] = None
    present_count: int
    percent: Optional[float] = None

class TeacherDailyResponse(BaseModel):
    date: str
    items: List[TeacherDailyItem]
    total_teachers: int
    total_present: int

@api.get("/attendance/teachers/daily", response_model=TeacherDailyResponse)
async def teachers_daily(date: Optional[str] = None, school_id: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN'))):
    day = (date or datetime.now(timezone.utc).date().isoformat())
    # Determine teacher scope
    teacher_query: Dict[str, Any] = {"role": "TEACHER"}
    if current['role'] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        teacher_query['school_id'] = current.get('school_id')
    elif current['role'] == 'GOV_ADMIN' and school_id:
        teacher_query['school_id'] = school_id
    teachers = await db.users.find(teacher_query).to_list(10000)
    teacher_ids = [t['id'] for t in teachers]
    if not teacher_ids:
        return TeacherDailyResponse(date=day, items=[], total_teachers=0, total_present=0)
    # Present counts per teacher for the day
    att_agg = db.attendance.aggregate([
        {"$match": {"teacher_id": {"$in": teacher_ids}, "date": day, "status": "Present"}},
        {"$group": {"_id": "$teacher_id", "present": {"$sum": 1}}}
    ])
    present_by_teacher: Dict[str, int] = {}
    async for g in att_agg:
        present_by_teacher[g['_id']] = int(g['present'])
    # Map sections
    section_map: Dict[str, Dict[str, Any]] = {}
    sec_ids = [t.get('section_id') for t in teachers if t.get('section_id')]
    if sec_ids:
        secs = await db.sections.find({"id": {"$in": sec_ids}}).to_list(10000)
        for s in secs:
            section_map[s['id']] = s
    # Student totals per teacher's section
    totals_by_section: Dict[str, int] = {}
    if sec_ids:
        st_agg = db.students.aggregate([
            {"$match": {"section_id": {"$in": sec_ids}}},
            {"$group": {"_id": "$section_id", "total": {"$sum": 1}}}
        ])
        async for g in st_agg:
            totals_by_section[g['_id']] = int(g['total'])
    items: List[TeacherDailyItem] = []
    total_present = 0
    for t in teachers:
        pres = int(present_by_teacher.get(t['id'], 0))
        total_present += pres
        sec_id = t.get('section_id')
        sec = section_map.get(sec_id) if sec_id else None
        tot = totals_by_section.get(sec_id) if sec_id else None
        pct = (round((pres / tot) * 100, 2) if tot and tot > 0 else None)
        items.append(TeacherDailyItem(
            teacher_id=t['id'], name=t.get('full_name') or 'Teacher', email=t.get('email'),
            section_id=sec_id, section_name=(sec.get('name') if sec else None), total_students=(int(tot) if isinstance(tot, int) else None),
            present_count=pres, percent=pct
        ))
    return TeacherDailyResponse(date=day, items=items, total_teachers=len(items), total_present=total_present)

class SchoolDailyItem(BaseModel):
    school_id: str
    name: str
    total_students: int
    present_count: int
    percent: float

class SchoolDailyResponse(BaseModel):
    date: str
    items: List[SchoolDailyItem]
    total_schools: int
    total_students: int
    total_present: int

@api.get("/attendance/schools/daily", response_model=SchoolDailyResponse)
async def schools_daily(date: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN'))):
    day = (date or datetime.now(timezone.utc).date().isoformat())
    schools = await db.schools.find({}).to_list(10000)
    if not schools:
        return SchoolDailyResponse(date=day, items=[], total_schools=0, total_students=0, total_present=0)
    # Map school -> section_ids
    school_sections: Dict[str, List[str]] = {}
    secs = await db.sections.find({}).to_list(100000)
    for s in secs:
        school_sections.setdefault(s['school_id'], []).append(s['id'])
    # Students totals per section
    st_agg = db.students.aggregate([
        {"$group": {"_id": "$section_id", "total": {"$sum": 1}}}
    ])
    students_per_section: Dict[str, int] = {}
    async for g in st_agg:
        students_per_section[g['_id']] = int(g['total'])
    # Present per section on day
    att_agg = db.attendance.aggregate([
        {"$match": {"date": day, "status": "Present"}},
        {"$group": {"_id": "$section_id", "present": {"$sum": 1}}}
    ])
    present_per_section: Dict[str, int] = {}
    async for g in att_agg:
        present_per_section[g['_id']] = int(g['present'])
    items: List[SchoolDailyItem] = []
    total_students = 0
    total_present = 0
    for sch in schools:
        sec_ids2 = school_sections.get(sch['id'], [])
        tot = sum(students_per_section.get(x, 0) for x in sec_ids2)
        pres = sum(present_per_section.get(x, 0) for x in sec_ids2)
        pct = float(round((pres / tot) * 100, 2)) if tot > 0 else 0.0
        items.append(SchoolDailyItem(school_id=sch['id'], name=sch.get('name') or 'School', total_students=tot, present_count=pres, percent=pct))
        total_students += tot
        total_present += pres
    return SchoolDailyResponse(date=day, items=items, total_schools=len(items), total_students=total_students, total_present=total_present)

class TrendsDayItem(BaseModel):
    date: str
    total_students: int
    present_count: int
    percent: float

class TrendsResponse(BaseModel):
    items: List[TrendsDayItem]

@api.get("/attendance/trends", response_model=TrendsResponse)
async def attendance_trends(from_: Optional[str] = None, to: Optional[str] = None, school_id: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN'))):
    # Build date range inclusive
    today = datetime.now(timezone.utc).date()
    start = datetime.fromisoformat((from_ or today.isoformat())) if from_ else datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end = datetime.fromisoformat((to or today.isoformat())) if to else datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if end < start:
        start, end = end, start
    # Preload sections scope if school_id supplied
    sec_scope: Optional[List[str]] = None
    if school_id:
        secs = await db.sections.find({"school_id": school_id}).to_list(100000)
        sec_scope = [s['id'] for s in secs]
    # Students totals (constant across days) within scope if any
    total_students = 0
    if sec_scope is None:
        total_students = await db.students.count_documents({})
    else:
        total_students = await db.students.count_documents({"section_id": {"$in": sec_scope}})
    # Build per-day present counts using attendance
    days: List[TrendsDayItem] = []
    cur_date = start.date()
    last_date = end.date()
    while cur_date <= last_date:
        dstr = cur_date.isoformat()
        match_q: Dict[str, Any] = {"date": dstr, "status": "Present"}
        if sec_scope is not None:
            match_q["section_id"] = {"$in": sec_scope}
        present = await db.attendance.count_documents(match_q)
        pct = float(round((present / total_students) * 100, 2)) if total_students > 0 else 0.0
        days.append(TrendsDayItem(date=dstr, total_students=int(total_students), present_count=int(present), percent=pct))
        cur_date = (datetime.fromisoformat(dstr) + timedelta(days=1)).date()
    return TrendsResponse(items=days)


@api.delete("/sections/{section_id}")
async def delete_section(section_id: str, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'GOV_ADMIN'))):
    sec = await db.sections.find_one({"id": section_id})
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
    if current['role'] == 'SCHOOL_ADMIN' and sec.get('school_id') != current.get('school_id'):
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.students.delete_many({"section_id": section_id})
    await db.sections.delete_one({"id": section_id})
    return {"deleted": True}

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

# Students CRUD limited
@api.post("/students/create")
async def create_student_disabled():
    raise HTTPException(status_code=405, detail="Disabled: Use /api/enrollment/students for face enrollment only")

@api.put("/students/{student_id}", response_model=Student)
async def update_student(student_id: str, payload: StudentUpdate, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'GOV_ADMIN'))):
    stu = await db.students.find_one({"id": student_id})
    if not stu:
        raise HTTPException(status_code=404, detail="Student not found")
    sec = await db.sections.find_one({"id": stu['section_id']})
    if current['role'] == 'SCHOOL_ADMIN' and sec and sec.get('school_id') != current.get('school_id'):
        raise HTTPException(status_code=403, detail="Not allowed")
    upd = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not upd:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await db.students.update_one({"id": student_id}, {"$set": upd})
    stu = await db.students.find_one({"id": student_id})
    return Student(**stu)

@api.delete("/students/{student_id}")
async def delete_student(student_id: str, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'GOV_ADMIN'))):
    stu = await db.students.find_one({"id": student_id})
    if not stu:
        raise HTTPException(status_code=404, detail="Student not found")
    sec = await db.sections.find_one({"id": stu['section_id']})
    if current['role'] == 'SCHOOL_ADMIN' and sec and sec.get('school_id') != current.get('school_id'):
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.students.delete_one({"id": student_id})
    return {"deleted": True}

# Users
ALLOWED_SUBJECTS = ["Math", "Science", "English", "Social", "Telugu", "Hindi", "Other"]

@api.post("/users/teachers", response_model=UserPublic)
async def create_teacher(payload: TeacherCreateRequest, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'GOV_ADMIN'))):
    school_id = payload.school_id or current.get("school_id")
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN'):
        school_id = current.get("school_id")
    if not school_id:
        raise HTTPException(status_code=400, detail="school_id required")
    if payload.subject and payload.subject not in ALLOWED_SUBJECTS:
        raise HTTPException(status_code=400, detail="Invalid subject")
    # Validate sections
    section_ids: List[str] = []
    if payload.all_sections:
        section_ids = []  # denote all by flag
    else:
        if payload.section_ids:
            # validate all belong to school
            secs = await db.sections.find({"id": {"$in": payload.section_ids}}).to_list(10000)
            valid_ids = {s['id'] for s in secs if s.get('school_id') == school_id}
            if len(valid_ids) != len(payload.section_ids):
                raise HTTPException(status_code=400, detail="One or more sections invalid for this school")
            section_ids = list(valid_ids)
        elif payload.section_id:
            sec = await db.sections.find_one({"id": payload.section_id})
            if not sec or sec.get("school_id") != school_id:
                raise HTTPException(status_code=400, detail="Invalid section for this school")
            section_ids = [payload.section_id]
    temp_pass = payload.password or secrets.token_urlsafe(8)
    user_doc = {
        "id": str(uuid.uuid4()),
        "full_name": payload.full_name,
        "email": payload.email.lower(),
        "role": 'TEACHER',
        "phone": payload.phone,
        "school_id": school_id,
        "subject": payload.subject,
        # legacy single section for backward compatibility
        "section_id": (section_ids[0] if (not payload.all_sections and section_ids) else None),
        # new multi-section fields
        "section_ids": (section_ids if (not payload.all_sections) else []),
        "all_sections": bool(payload.all_sections),
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
        phone=user_doc.get("phone"), school_id=school_id, subject=user_doc.get("subject"), section_id=user_doc.get("section_id"), section_ids=user_doc.get("section_ids"), all_sections=bool(user_doc.get("all_sections")), created_at=user_doc["created_at"]
    )

@api.post("/users/coadmins", response_model=UserPublic)
async def create_coadmin(payload: CoadminCreateRequest, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN', 'GOV_ADMIN'))):
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
        school_id=u.get("school_id"), subject=u.get("subject"), section_id=u.get("section_id"), section_ids=u.get("section_ids"), all_sections=bool(u.get("all_sections", False)), created_at=u["created_at"]
    ) for u in items]}

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    subject: Optional[str] = None
    section_id: Optional[str] = None  # legacy single
    section_ids: Optional[List[str]] = None
    all_sections: Optional[bool] = None

@api.put("/users/{user_id}", response_model=UserPublic)
async def update_user(user_id: str, payload: UserUpdate, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN'))):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current['role'] == 'SCHOOL_ADMIN':
        if user.get('school_id') != current.get('school_id'):
            raise HTTPException(status_code=403, detail="Not allowed")
        if user.get('role') == 'SCHOOL_ADMIN' and user.get('id') != current.get('id'):
            pass
    upd = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if user.get('role') == 'TEACHER':
        if 'subject' in upd and upd['subject'] not in ALLOWED_SUBJECTS:
            raise HTTPException(status_code=400, detail="Invalid subject")
        # Normalize multi-section fields
        if 'all_sections' in upd and upd['all_sections']:
            upd['section_ids'] = []
            upd['section_id'] = None
        else:
            # validate provided section_ids / section_id
            # Prefer multi-section payload when present; do not override with legacy section_id
            if 'section_ids' in upd and isinstance(upd['section_ids'], list):
                if upd['section_ids']:
                    secs = await db.sections.find({"id": {"$in": upd['section_ids']}}).to_list(10000)
                    valid_ids = {s['id'] for s in secs}
                    # if SCHOOL_ADMIN, ensure same school
                    if current['role'] == 'SCHOOL_ADMIN':
                        valid_ids = {s['id'] for s in secs if s.get('school_id') == current.get('school_id')}
                    if len(valid_ids) != len(upd['section_ids']):
                        raise HTTPException(status_code=400, detail="One or more sections invalid")
                    upd['section_ids'] = list(valid_ids)
                # set legacy section_id for convenience but only derived from section_ids
                upd['section_id'] = (upd['section_ids'][0] if upd['section_ids'] else None)
            elif 'section_id' in upd and upd['section_id']:
                # Only handle legacy single section when multi not provided
                sec = await db.sections.find_one({"id": upd['section_id']})
                if not sec:
                    raise HTTPException(status_code=400, detail="Invalid section")
                if current['role'] == 'SCHOOL_ADMIN' and sec.get('school_id') != current.get('school_id'):
                    raise HTTPException(status_code=400, detail="Invalid section for this school")
                # ensure section_ids reflects this choice
                upd['section_ids'] = [upd['section_id']]
            if 'all_sections' not in upd:
                upd['all_sections'] = False
    await db.users.update_one({"id": user_id}, {"$set": upd})
    new_u = await db.users.find_one({"id": user_id})
    return UserPublic(
        id=new_u["id"], full_name=new_u["full_name"], email=new_u["email"], role=new_u["role"], phone=new_u.get("phone"),
        school_id=new_u.get("school_id"), subject=new_u.get("subject"), section_id=new_u.get("section_id"), section_ids=new_u.get("section_ids"), all_sections=bool(new_u.get("all_sections", False)), created_at=new_u["created_at"]
    )

@api.delete("/users/{user_id}")
async def delete_user(user_id: str, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN'))):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current['role'] == 'SCHOOL_ADMIN':
        if user.get('school_id') != current.get('school_id'):
            raise HTTPException(status_code=403, detail="Not allowed")
        if user.get('role') == 'SCHOOL_ADMIN':
            raise HTTPException(status_code=403, detail="Cannot delete a School Admin")
    await db.users.delete_one({"id": user_id})
    return {"deleted": True}

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

# ---------- Startup ----------
@api.get("/debug-route-2024")
async def debug_route_unique():
    return {"message": "Debug route working", "timestamp": "2024-test", "working": True}

@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.schools.create_index("name")
    await db.sections.create_index("school_id")
    await db.students.create_index("section_id")
    await db.students.create_index("twin_group_id")
    await db.attendance.create_index([("section_id", 1), ("date", 1), ("student_id", 1)], unique=True)
    await db.attendance_sessions.create_index([("teacher_id", 1), ("date", 1)])

    try:
        gov_email = os.getenv("SEED_GOV_ADMIN_EMAIL")
        gov_name = os.getenv("SEED_GOV_ADMIN_NAME") or "Gov Admin"
        gov_pass = os.getenv("SEED_GOV_ADMIN_PASSWORD")
        school_name = os.getenv("SEED_SCHOOL_NAME")
        school_admin_email = os.getenv("SEED_SCHOOL_ADMIN_EMAIL")
        school_admin_name = os.getenv("SEED_SCHOOL_ADMIN_NAME") or "School Admin"
        school_admin_pass = os.getenv("SEED_SCHOOL_ADMIN_PASSWORD")
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