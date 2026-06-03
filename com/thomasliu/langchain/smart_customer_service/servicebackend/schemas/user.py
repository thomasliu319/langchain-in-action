from datetime import datetime
from typing import Optional

from pydantic import BaseModel


#用户基础模型
class UserBase(BaseModel):

    username:str

    email:str

#注册模型
class UserCreate(UserBase):

    password:str

# 用户响应模型
class UserResponse(UserBase):

    id:int

    created_at: datetime

    updated_at: datetime

    #启用 ORM 属性映射模型，允许从 ROM实例自动读取属性
    class Config:
        from_attributes = True

#token 响应模型
class Token(BaseModel):

    access_token:str

    token_type:str

    user_id:int


#Tokne 数据模型：用于 解析jwt 令牌
class TokenData(BaseModel):

    user_id: Optional[int] = None