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
    student_code: Optional[str] = None
    roll_no: Optional[str] = None
    section_id: str
    parent_mobile: Optional[str] = None
    has_twin: bool = False
    twin_group_id: Optional[str] = None
    twin_of: Optional[str] = None  # link to sibling student id

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    student_code: Optional[str] = None
    roll_no: Optional[str] = None
    parent_mobile: Optional[str] = None

class Student(BaseModel):
    id: str
    name: str
    student_code: str
    roll_no: Optional[str] = None
    section_id: str
    parent_mobile: Optional[str] = None
    has_twin: bool
    twin_group_id: Optional[str]
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
            
            # Initialize with minimal configuration to avoid container issues
            FACE_MESH = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=False,  # Disable to reduce complexity
                min_detection_confidence=0.3,  # Lower threshold
                min_tracking_confidence=0.3
            )
            logger.info("MediaPipe Face Mesh initialized successfully")
        except Exception as e:
            logger.warning(f"MediaPipe Face Mesh not available or failed to initialize: {e}")
            # Try alternative initialization
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

async def _detect_and_crop_face_mesh(image_bytes: bytes):
    """
    Detect face using MediaPipe Face Mesh and crop the face region
    """
    try:
        import numpy as np
        import cv2
        
        face_mesh = await _ensure_face_mesh()
        if face_mesh is None:
            return None, "face_mesh_not_available"
            
        npimg = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if img is None:
            return None, "decode_failed"
            
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        
        if results and results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            h, w, c = img.shape
            
            # Get face bounding box from landmarks
            x_coords = [landmark.x * w for landmark in landmarks.landmark]
            y_coords = [landmark.y * h for landmark in landmarks.landmark]
            
            x1 = max(int(min(x_coords)) - 20, 0)
            y1 = max(int(min(y_coords)) - 20, 0)
            x2 = min(int(max(x_coords)) + 20, w)
            y2 = min(int(max(y_coords)) + 20, h)
            
            if x2 <= x1 or y2 <= y1:
                return None, "invalid_bbox"
                
            face = img[y1:y2, x1:x2]
            return face, None
            
        return None, "no_face"
        
    except Exception as e:
        logger.exception("Face mesh detection error")
        return None, str(e)

async def _embed_face_with_mobilefacenet(face_bgr):
    """
    Generate face embedding using MobileFaceNet TFLite model
    """
    try:
        import numpy as np
        import cv2
        
        model = await _ensure_mobilefacenet_model()
        if model is None:
            return None, "mobilefacenet_not_available"
            
        # Preprocess face for MobileFaceNet (112x112, normalized)
        face_resized = cv2.resize(face_bgr, (112, 112))
        face_normalized = (face_resized.astype(np.float32) - 127.5) / 128.0
        face_input = np.expand_dims(face_normalized, axis=0)
        
        # Get input and output details
        input_details = model.get_input_details()
        output_details = model.get_output_details()
        
        # Set input tensor
        model.set_tensor(input_details[0]['index'], face_input)
        
        # Run inference
        model.invoke()
        
        # Get output embedding
        embedding = model.get_tensor(output_details[0]['index'])
        embedding = embedding[0]  # Remove batch dimension
        
        # Normalize embedding (L2 normalization)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding.tolist(), None
        
    except Exception as e:
        logger.exception("MobileFaceNet embedding error")
        return None, str(e)

def _cosine_sim(a: List[float], b: List[float]) -> float:
    import math
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0:
        return -1.0
    return dot / (na * nb)


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
    return {"message": "API ok", "debug": "root route working"}
    # remove unused variable


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

# TEMP: Testing route registration issue
@api.get("/debug-route-2024")
async def debug_route_unique():
    return {"message": "Debug route working", "timestamp": "2024-test", "working": True}

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

@api.put("/schools/{school_id}", response_model=School)
async def update_school(school_id: str, payload: SchoolUpdate, _: dict = Depends(require_roles('GOV_ADMIN'))):
    upd = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not upd:
        raise HTTPException(status_code=400, detail="Nothing to update")
    # if principal_email changes, ensure no user conflict
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
    # cascade: sections, students, users in this school
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
async def update_section(section_id: str, payload: SectionUpdate, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'GOV_ADMIN'))):  # noqa: E501
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
# List students
@api.get("/students", response_model=List[Student])
async def list_students(section_id: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER'))):
    query: Dict[str, Any] = {}
    if section_id:
        query["section_id"] = section_id
    if current['role'] in ('SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER') and current.get('school_id'):
        # Ensure sections belong to current school
        school_sections = await db.sections.find({"school_id": current.get('school_id')}).to_list(10000)
        allowed_sec_ids = {s['id'] for s in school_sections}
        if section_id and section_id not in allowed_sec_ids:
            raise HTTPException(status_code=403, detail="Not allowed for this section")
        if not section_id:
            query["section_id"] = {"$in": list(allowed_sec_ids)}
    # Only return students that have face embeddings (enrolled)
    query["embeddings.0"] = {"$exists": True}
    items = await db.students.find(query).to_list(10000)
    return [Student(**i) for i in items]

# Student search endpoint to help find twins by name/roll/student_code
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
    # Build base filter
    flt: Dict[str, Any] = {
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"roll_no": {"$regex": query, "$options": "i"}},
            {"student_code": {"$regex": query, "$options": "i"}},
        ]
    }

    # Scope to section if provided
    if section_id:
        flt["section_id"] = section_id
    else:
        # For school roles/teacher, restrict to their school's sections
        if current.get("role") in ("SCHOOL_ADMIN", "CO_ADMIN", "TEACHER") and current.get("school_id"):
            secs = await db.sections.find({"school_id": current.get("school_id")}).to_list(10000)
            allowed = [s["id"] for s in secs]
            flt["section_id"] = {"$in": allowed}

    docs = await db.students.find(flt).limit(25).to_list(100)
    items = [StudentSearchItem(id=d["id"], name=d["name"], section_id=d["section_id"], roll_no=d.get("roll_no"), student_code=d.get("student_code")) for d in docs]
    return {"items": items}

    return [Student(**i) for i in items]


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
    has_twin: bool = Form(False),
    twin_group_id: Optional[str] = Form(None),
    twin_of: Optional[str] = Form(None),
    images: List[UploadFile] = File(...),
    current: dict = Depends(require_roles('SCHOOL_ADMIN', 'CO_ADMIN')),
):
    logger.info("Face enrollment endpoint called successfully!")  # Debug log
    # Validate section scope
    sec = await db.sections.find_one({"id": section_id})  # noqa: F841
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
    if current["role"] in ('SCHOOL_ADMIN', 'CO_ADMIN') and sec.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Not your school section")

    # Process images to embeddings using MediaPipe Face Mesh + MobileFaceNet
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

    # If twin_of provided, validate it belongs to same section and exists
    if twin_of:
        other = await db.students.find_one({"id": twin_of})
        if not other:
            raise HTTPException(status_code=404, detail="Provided twin_of student not found")
        if other.get("section_id") != section_id:
            raise HTTPException(status_code=400, detail="Twin must be in the same section")
        has_twin = True
        # If no twin_group_id, inherit or create
        if not twin_group_id:
            twin_group_id = other.get("twin_group_id") or other.get("id")

    doc = {
        "id": sid,
        "name": name,
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

    # If twin_of provided and the other twin has no twin_of, update it to link back
    if twin_of and other and not other.get("twin_of"):
        await db.students.update_one({"id": twin_of}, {"$set": {"twin_of": sid, "has_twin": True, "twin_group_id": doc["twin_group_id"]}})

    return StudentEnrollResponse(id=sid, name=name, section_id=section_id, parent_mobile=parent_mobile, embeddings_count=len(embeddings), has_twin=bool(has_twin), twin_of=twin_of)

# Test route to debug route registration
@api.get("/test-route")
async def test_route():
    return {"message": "Test route works", "routes_registered": True}

# Simple test endpoint to verify route registration
@api.get("/route-test")
async def simple_route_test():
    return {"message": "Route registration working", "path": "/route-test"}

# Debug route for students
@api.get("/students-debug")
async def debug_students():
    return {"message": "Students debug route works", "count": await db.students.count_documents({})}

# Simple test endpoint to debug GET method
@api.get("/students-simple")
async def simple_students_test():
    return {"message": "Simple GET endpoint working", "method": "GET"}

# Preflight support for CORS-sensitive routes
@api.options("/enrollment/students")
async def options_students_enroll():
    return {"ok": True}

@api.options("/attendance/mark")
async def options_attendance_mark():
    return {"ok": True}

class AttendanceMarkResponse(BaseModel):
    status: str
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    similarity: Optional[float] = None
    twin_conflict: bool = False
    twin_candidates: Optional[List[Dict[str, str]]] = None  # when confirmation is needed

@api.post("/attendance/mark", response_model=AttendanceMarkResponse)
async def mark_attendance(
    image: UploadFile = File(...),
    section_id: Optional[str] = Form(None),
    confirmed_student_id: Optional[str] = Form(None),
    current: dict = Depends(require_roles('TEACHER')),
):
    # Determine section to mark against: provided or teacher's default
    chosen_section = section_id or current.get("section_id")
    if not chosen_section:
        raise HTTPException(status_code=400, detail="No section specified and teacher has no default section")

    # If teacher already resolved twin ambiguity on client side
    if confirmed_student_id:
        stu = await db.students.find_one({"id": confirmed_student_id, "section_id": chosen_section})
        if not stu:
            raise HTTPException(status_code=400, detail="Confirmed student not found in section")
        # Prevent duplicate for today
        today = datetime.now(timezone.utc).date()
        start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        existing = await db.attendance.find_one({"student_id": confirmed_student_id, "section_id": chosen_section, "timestamp": {"$gte": start, "$lt": end}})
        if existing:
            return AttendanceMarkResponse(status="Already marked present", student_id=confirmed_student_id, student_name=stu["name"], similarity=None, twin_conflict=False)
        rec = {
            "id": str(uuid.uuid4()),
            "date": start.date().isoformat(),
            "section_id": chosen_section,
            "student_id": confirmed_student_id,
            "status": "Present",
            "teacher_id": current["id"],
            "timestamp": now_iso(),
        }
        await db.attendance.insert_one(rec)
        return AttendanceMarkResponse(status=f"{stu['name']} is marked present, scan next student", student_id=confirmed_student_id, student_name=stu["name"], similarity=None, twin_conflict=False)

    # Validate section belongs to teacher's school
    sec = await db.sections.find_one({"id": chosen_section})
    if not sec or sec.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Invalid section for this teacher")

    data = await image.read()
    face, err = await _detect_and_crop_face_mesh(data)
    if face is None:
        raise HTTPException(status_code=400, detail=f"No face detected: {err}")
    emb, e2 = await _embed_face_with_mobilefacenet(face)
    if not emb:
        raise HTTPException(status_code=400, detail=f"No embedding generated: {e2}")

    # Load students for this section only
    students = await db.students.find({"section_id": chosen_section}).to_list(2000)
    best_id = None
    best_name = None
    best_sim = -1.0
    twin_conflict = False

    for s in students:
        s_embs = s.get("embeddings", [])
        sims = [_cosine_sim(emb, e) for e in s_embs if isinstance(e, list)]
        sim = max(sims) if sims else -1.0
        if sim > best_sim:
            best_sim = sim
            best_id = s["id"]
            best_name = s["name"]

    threshold = 0.90  # 90%
    if best_sim < threshold:
        return AttendanceMarkResponse(status="Not a student from this section")

    # Determine twin situation
    stu = await db.students.find_one({"id": best_id})
    twin_conflict = False
    if stu and stu.get("has_twin") and stu.get("twin_group_id"):
        # fetch other twins in same group in this section
        twins = await db.students.find({
            "section_id": chosen_section,
            "twin_group_id": stu["twin_group_id"]
        }).to_list(10)
        # If 2+ students in group, we may need disambiguation
        if len(twins) >= 2:
            # Check who is already marked today
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

            # If one twin already present and the other not, auto-assign to other
            unmarked_twins = [t for t in twins if t["id"] not in present_ids]
            if len(unmarked_twins) == 1:
                # Auto-assign to the only unmarked twin
                best_id = unmarked_twins[0]["id"]
                best_name = unmarked_twins[0]["name"]
            elif len(unmarked_twins) >= 2:
                # Ambiguous: return a message requesting confirmation with both IDs
                twin_conflict = True
                candidates = [{"id": t["id"], "name": t["name"]} for t in twins]
                return AttendanceMarkResponse(status="Twin detected. Please confirm who it is.", twin_conflict=True, twin_candidates=candidates)

    # Prevent duplicate for today
    today = datetime.now(timezone.utc).date()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    existing = await db.attendance.find_one({"student_id": best_id, "section_id": chosen_section, "timestamp": {"$gte": start, "$lt": end}})
    if existing:
        return AttendanceMarkResponse(status="Already marked present", student_id=best_id, student_name=best_name, similarity=best_sim, twin_conflict=twin_conflict)

    rec = {
        "id": str(uuid.uuid4()),
        "date": start.date().isoformat(),
        "section_id": chosen_section,
        "student_id": best_id,
        "status": "Present",
        "teacher_id": current["id"],
        "timestamp": now_iso(),
    }
    await db.attendance.insert_one(rec)
    return AttendanceMarkResponse(status=f"{best_name} is marked present, scan next student", student_id=best_id, student_name=best_name, similarity=best_sim, twin_conflict=twin_conflict)

class AttendanceSummaryItem(BaseModel):
    student_id: str
    name: str
    present: bool

class AttendanceSummary(BaseModel):
    section_id: str
    date: str
    total: int
    present_count: int
    items: List[AttendanceSummaryItem]

@api.get("/attendance/summary", response_model=AttendanceSummary)
async def attendance_summary(section_id: str, date: Optional[str] = None, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER'))):
    # Scope check for school admins and teachers
    sec = await db.sections.find_one({"id": section_id})  # noqa: F841
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
    if current['role'] in ('SCHOOL_ADMIN', 'CO_ADMIN', 'TEACHER') and sec.get('school_id') != current.get('school_id'):
        raise HTTPException(status_code=403, detail="Not allowed")

    if date is None:
        today = datetime.now(timezone.utc).date()
        date = today.isoformat()

    students = await db.students.find({"section_id": section_id}).to_list(5000)
    # ids not used in response; keep for potential future use
    ids = [s['id'] for s in students]  # noqa: F841
    atts = await db.attendance.find({"section_id": section_id, "date": date}).to_list(10000)
    present_ids = {a['student_id'] for a in atts if a.get('status') == 'Present'}
    items = [AttendanceSummaryItem(student_id=s['id'], name=s['name'], present=s['id'] in present_ids) for s in students]
    return AttendanceSummary(section_id=section_id, date=date, total=len(students), present_count=len(present_ids), items=items)

@api.delete("/sections/{section_id}")
async def delete_section(section_id: str, current: dict = Depends(require_roles('SCHOOL_ADMIN', 'GOV_ADMIN'))):
    sec = await db.sections.find_one({"id": section_id})  # noqa: F841
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

# Students
@api.post("/students/create", response_model=Student)
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

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    subject: Optional[str] = None
    section_id: Optional[str] = None

@api.put("/users/{user_id}", response_model=UserPublic)
async def update_user(user_id: str, payload: UserUpdate, current: dict = Depends(require_roles('GOV_ADMIN', 'SCHOOL_ADMIN'))):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current['role'] == 'SCHOOL_ADMIN':
        if user.get('school_id') != current.get('school_id'):
            raise HTTPException(status_code=403, detail="Not allowed")
        if user.get('role') == 'SCHOOL_ADMIN' and user.get('id') != current.get('id'):
            # prevent school admin editing other school admins arbitrarily
            pass
    upd = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    # validate teacher subject/section
    if user.get('role') == 'TEACHER':
        if 'subject' in upd and upd['subject'] not in ALLOWED_SUBJECTS:
            raise HTTPException(status_code=400, detail="Invalid subject")
        if 'section_id' in upd and upd['section_id']:
            sec = await db.sections.find_one({"id": upd['section_id']})
            if not sec or (current['role'] == 'SCHOOL_ADMIN' and sec.get('school_id') != current.get('school_id')):
                raise HTTPException(status_code=400, detail="Invalid section for this school")
    await db.users.update_one({"id": user_id}, {"$set": upd})
    new_u = await db.users.find_one({"id": user_id})
    return UserPublic(
        id=new_u["id"], full_name=new_u["full_name"], email=new_u["email"], role=new_u["role"], phone=new_u.get("phone"),
        school_id=new_u.get("school_id"), subject=new_u.get("subject"), section_id=new_u.get("section_id"), created_at=new_u["created_at"]
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
    await db.students.create_index("twin_group_id")
    await db.attendance.create_index([("section_id", 1), ("date", 1), ("student_id", 1)], unique=True)

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
