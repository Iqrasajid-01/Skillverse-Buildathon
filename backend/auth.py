"""
Authentication Module - User Auth with Email OTP + PostgreSQL
"""
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from database import SessionLocal, init_db, engine

# Password hashing - use bcrypt directly
import bcrypt
USE_DIRECT_BCRYPT = True

# SQLAlchemy Base
Base = declarative_base()

# ============ DATABASE MODELS ============
class UserModel(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), default="")
    last_name = Column(String(100), default="")
    country = Column(String(100), default="Pakistan")
    city = Column(String(100), default="")
    address = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, default=datetime.now)
    is_verified = Column(Boolean, default=False)
    auth_provider = Column(String(20), default="email")

class OTPModel(Base):
    """Email OTP verification model"""
    __tablename__ = "email_otps"
    
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, index=True)
    otp = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

class PendingUserModel(Base):
    """Pending user registration (before OTP verification)"""
    __tablename__ = "pending_users"
    
    id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), default="")
    last_name = Column(String(100), default="")
    country = Column(String(100), default="Pakistan")
    city = Column(String(100), default="")
    address = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)

class SessionModel(Base):
    """Session tokens model"""
    __tablename__ = "sessions"
    
    token = Column(String(200), primary_key=True)
    user_id = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)


# ============ AUTH SERVICE ============
class AuthService:
    """
    Authentication service with Email OTP + Password
    """
    
    def __init__(self):
        self.otp_expiry_minutes = 15
        self.max_otp_attempts = 3
        self.session_expiry_hours = 24 * 7
        self.pending_user_expiry_minutes = 60
        self._init_tables()
    
    def _init_tables(self):
        """Create tables if they don't exist"""
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"DB init warning: {e}")
    
    def _get_db(self):
        """Get database session"""
        return SessionLocal()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    def generate_session_token(self) -> str:
        """Generate secure session token"""
        return f"cs_{uuid.uuid4().hex}_{datetime.now().timestamp()}"
    
    def check_email_exists(self, email: str) -> bool:
        """Check if email already registered"""
        db = self._get_db()
        try:
            email = email.lower().strip()
            user = db.query(UserModel).filter(UserModel.email == email).first()
            return user is not None
        finally:
            db.close()
    
    def send_email_otp(self, email: str, user_data: Dict) -> Dict:
        """Send OTP to email for registration"""
        db = self._get_db()
        try:
            email = email.lower().strip()
            
            # Check if email already exists
            if self.check_email_exists(email):
                raise HTTPException(status_code=400, detail="Email already registered. Please login.")
            
            # Delete any existing pending registration for this email
            db.query(PendingUserModel).filter(PendingUserModel.email == email).delete()
            db.query(OTPModel).filter(OTPModel.email == email).delete()
            
            # Generate OTP
            otp = self.generate_otp()
            expires_at = datetime.now() + timedelta(minutes=self.otp_expiry_minutes)
            
            # Store OTP
            otp_record = OTPModel(
                email=email,
                otp=otp,
                expires_at=expires_at,
                attempts=0
            )
            db.add(otp_record)
            
            # Store pending user data
            pending_user = PendingUserModel(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=self.hash_password(user_data['password']),
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                country=user_data.get('country', 'Pakistan'),
                city=user_data.get('city', ''),
                address=user_data.get('address', ''),
                expires_at=datetime.now() + timedelta(minutes=self.pending_user_expiry_minutes)
            )
            db.add(pending_user)
            db.commit()
            
            # TODO: Integrate with email service (SendGrid, SMTP, etc.)
            # For now, log OTP (REMOVE IN PRODUCTION)
            print(f"\n{'='*50}")
            print(f"[EMAIL] OTP for: {email}")
            print(f"[OTP] {otp}")
            print(f"[EXPIRES] in {self.otp_expiry_minutes} minutes")
            print(f"{'='*50}\n")
            
            return {
                "status": "sent",
                "message": f"OTP sent to {email}",
                "email": email,
                "expires_in_seconds": self.otp_expiry_minutes * 60,
                "otp_for_testing": otp  # DEV ONLY
            }
        finally:
            db.close()
    
    def verify_email_otp(self, email: str, otp: str) -> Dict:
        """Verify OTP and create user account"""
        db = self._get_db()
        try:
            email = email.lower().strip()
            
            # Get pending user
            pending_user = db.query(PendingUserModel).filter(
                PendingUserModel.email == email
            ).first()
            
            if not pending_user:
                raise HTTPException(status_code=400, detail="No pending registration. Please sign up first.")
            
            # Check expiry
            if datetime.now() > pending_user.expires_at:
                db.delete(pending_user)
                db.commit()
                raise HTTPException(status_code=400, detail="Registration expired. Please sign up again.")
            
            # Get OTP record
            otp_record = db.query(OTPModel).filter(OTPModel.email == email).first()
            
            if not otp_record:
                raise HTTPException(status_code=400, detail="OTP not sent. Please request a new one.")
            
            if datetime.now() > otp_record.expires_at:
                db.delete(otp_record)
                db.commit()
                raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")
            
            if otp_record.attempts >= self.max_otp_attempts:
                db.delete(otp_record)
                db.delete(pending_user)
                db.commit()
                raise HTTPException(status_code=400, detail="Too many attempts. Please request a new OTP.")
            
            # Verify OTP
            if otp_record.otp != otp:
                otp_record.attempts += 1
                db.commit()
                remaining = self.max_otp_attempts - otp_record.attempts
                raise HTTPException(status_code=400, detail=f"Invalid OTP. {remaining} attempts remaining.")
            
            # Success - Create user
            user_id = str(uuid.uuid4())
            user = UserModel(
                id=user_id,
                email=pending_user.email,
                password_hash=pending_user.password_hash,
                first_name=pending_user.first_name,
                last_name=pending_user.last_name,
                country=pending_user.country,
                city=pending_user.city,
                address=pending_user.address,
                is_verified=True
            )
            db.add(user)
            
            # Delete OTP and pending user
            db.delete(otp_record)
            db.delete(pending_user)
            db.commit()
            
            # Create session
            session_token = self.generate_session_token()
            expires_at = datetime.now() + timedelta(hours=self.session_expiry_hours)
            
            session = SessionModel(
                token=session_token,
                user_id=user_id,
                expires_at=expires_at
            )
            db.add(session)
            db.commit()
            
            return {
                "status": "verified",
                "user_id": user_id,
                "session_token": session_token,
                "user": self._user_to_dict(user)
            }
        finally:
            db.close()
    
    def resend_otp(self, email: str) -> Dict:
        """Resend OTP for pending registration"""
        db = self._get_db()
        try:
            email = email.lower().strip()
            
            # Get pending user
            pending_user = db.query(PendingUserModel).filter(
                PendingUserModel.email == email
            ).first()
            
            if not pending_user:
                raise HTTPException(status_code=400, detail="No pending registration. Please sign up first.")
            
            # Delete old OTP
            db.query(OTPModel).filter(OTPModel.email == email).delete()
            
            # Generate new OTP
            otp = self.generate_otp()
            expires_at = datetime.now() + timedelta(minutes=self.otp_expiry_minutes)
            
            otp_record = OTPModel(
                email=email,
                otp=otp,
                expires_at=expires_at,
                attempts=0
            )
            db.add(otp_record)
            db.commit()
            
            print(f"\n[RESEND] OTP for {email}: {otp}\n")
            
            return {
                "status": "sent",
                "message": f"New OTP sent to {email}",
                "email": email,
                "expires_in_seconds": self.otp_expiry_minutes * 60,
                "otp_for_testing": otp  # DEV ONLY
            }
        finally:
            db.close()
    
    def login(self, email: str, password: str) -> Dict:
        """Login with email and password"""
        db = self._get_db()
        try:
            email = email.lower().strip()
            
            user = db.query(UserModel).filter(UserModel.email == email).first()
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid email or password.")
            
            if not self.verify_password(password, user.password_hash):
                raise HTTPException(status_code=401, detail="Invalid email or password.")
            
            # Update last login
            user.last_login = datetime.now()
            db.commit()
            
            # Create session
            session_token = self.generate_session_token()
            expires_at = datetime.now() + timedelta(hours=self.session_expiry_hours)
            
            session = SessionModel(
                token=session_token,
                user_id=user.id,
                expires_at=expires_at
            )
            db.add(session)
            db.commit()
            
            return {
                "status": "success",
                "session_token": session_token,
                "user": self._user_to_dict(user)
            }
        finally:
            db.close()
    
    def validate_session(self, session_token: str) -> Optional[Dict]:
        """Validate session token and return user"""
        db = self._get_db()
        try:
            session = db.query(SessionModel).filter(SessionModel.token == session_token).first()
            
            if not session:
                return None
            
            if datetime.now() > session.expires_at:
                db.delete(session)
                db.commit()
                return None
            
            user = db.query(UserModel).filter(UserModel.id == session.user_id).first()
            if user:
                return self._user_to_dict(user)
            return None
        finally:
            db.close()
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        db = self._get_db()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user:
                return self._user_to_dict(user)
            return None
        finally:
            db.close()
    
    def update_profile(self, user_id: str, data: Dict) -> Dict:
        """Update user profile"""
        db = self._get_db()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            allowed_fields = ['first_name', 'last_name', 'country', 'city', 'address']
            for field in allowed_fields:
                if field in data and data[field] is not None:
                    setattr(user, field, data[field])
            
            db.commit()
            return {"status": "success", "user": self._user_to_dict(user)}
        finally:
            db.close()
    
    def update_password(self, user_id: str, old_password: str, new_password: str) -> Dict:
        """Update user password"""
        db = self._get_db()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if not self.verify_password(old_password, user.password_hash):
                raise HTTPException(status_code=400, detail="Current password is incorrect.")
            
            user.password_hash = self.hash_password(new_password)
            db.commit()
            return {"status": "success", "message": "Password updated successfully"}
        finally:
            db.close()
    
    def logout(self, session_token: str) -> bool:
        """End user session"""
        db = self._get_db()
        try:
            db.query(SessionModel).filter(SessionModel.token == session_token).delete()
            db.commit()
            return True
        finally:
            db.close()
    
    def _user_to_dict(self, user) -> Dict:
        """Convert user to dictionary"""
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "country": user.country,
            "city": user.city,
            "address": user.address or "",
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "is_verified": user.is_verified,
            "auth_provider": user.auth_provider
        }


# Global auth service instance
auth_service = AuthService()