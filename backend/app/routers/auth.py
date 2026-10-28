from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os
from app.models import RoleEnum

from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "pln-kwh-secret-key-ganti-di-production")
ALGORITHM = "HS256"

from fastapi import Request, Response

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Token tidak valid",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Prioritaskan token dari cookie (HTTP-Only)
    cookie_token = request.cookies.get("access_token")
    final_token = cookie_token or token

    if not final_token:
        raise credentials_exception

    try:
        payload = jwt.decode(final_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

def create_token(data: dict, expires_hours: int = 8):
    expire = datetime.utcnow() + timedelta(hours=expires_hours)
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

from fastapi import Request
from app.limiter import limiter

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=req.username, is_active=True).first()
    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    token = create_token({"sub": str(user.id), "role": user.role.value})
    
    # Set HTTP-Only Cookie
    response.set_cookie(
        key="access_token", 
        value=token, 
        httponly=True, 
        max_age=8 * 3600, 
        samesite="lax"
    )
    
    return TokenResponse(
        access_token="", # Kosongkan karena sudah di cookie
        role=user.role.value,
        full_name=user.full_name,
        kode_unit=user.kode_unit
    )

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Berhasil logout"}

@router.post("/init-admin")
def init_admin(db: Session = Depends(get_db)):
    existing = db.query(User).filter_by(username="admin").first()
    if existing:
        # Upgrade role ke super_admin jika masih role lama
        if existing.role.value not in ["super_admin", "uid", "up3", "ulp", "verifikator"]:
            existing.role = RoleEnum.super_admin
            db.commit()
        return {"message": "Admin sudah ada", "role": existing.role.value}
    admin = User(
        username="admin",
        password_hash=pwd_context.hash("admin123"),
        full_name="Administrator PLN",
        role=RoleEnum.super_admin
    )
    db.add(admin)
    db.commit()
    return {"message": "Admin berhasil dibuat", "username": "admin", "password": "admin123"}