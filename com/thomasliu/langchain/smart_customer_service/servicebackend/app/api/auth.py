from datetime import timedelta, datetime

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config.settings  import settings
from app.database.mysql import get_db
from app.models.user import User
from schemas.user import TokenData, UserResponse, UserCreate, Token

#创建 认证 路由实例
router = APIRouter()


#OAuth2 令牌获取方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


#验证密码
def verify_password(plain_password: str, hashed_password: str) -> bool:

    truncated_password = plain_password[:72]

    return bcrypt.checkpw(truncated_password.encode('utf-8'), hashed_password.encode('utf-8'))


#获取密码哈希值
def get_password_hash(password: str)-> str:
    truncated_password = password[:72]

    salt = bcrypt.gensalt()

    return bcrypt.hashpw(truncated_password.encode('utf-8'), salt).decode('utf-8')



#认证用户，验证 用户名 和 密码 是否正确
def authenticate_user(db: Session, username: str, password: str) :

    user = db.query(User).filter(User.username == username).first()

    if not user:
        return False

    if not verify_password(password, user.password_hash):
        return False

    return user

#创建令牌
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encode_jwt


#解析令牌 获取用户信息
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db) ):
    # 定义 认证 异常
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        user_id = payload.get("sub")

        token_data = TokenData(user_id=int(user_id))
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()

    if not user:
        raise credentials_exception
    return user

#注册

@router.post("/register",response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
        if existing_user:
            if existing_user.username == user.username:
                raise HTTPException(status_code=400, detail="用户名已经存在")
            if existing_user.email == user.email:
                raise HTTPException(status_code=400, detail="邮箱已经存在")


        hashed_password = get_password_hash(user.password)

        db_user = User(
            username=user.username,
            email=user.email,
            password_hash=hashed_password
        )

        db.add(db_user)

        db.commit()

        #刷新用户对象 获取 数据库创建数据时 的 id、创建时间等
        db.refresh(db_user)

        return db_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务内部错误: {str(e)}")


@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, form_data.username, form_data.password)

        if not user:
            raise  HTTPException(status_code=401, detail="用户名或密码错误")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

        return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务内部错误: {str(e)}")






