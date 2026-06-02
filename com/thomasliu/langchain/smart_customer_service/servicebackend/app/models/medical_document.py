from sqlalchemy import Column, String, Integer, func, DateTime

from app.database.postgresql import PostgresBase


#文件上传记录
class MedicalDocument(PostgresBase):
    __tablename__ = 'medical_documents'

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(String(100), nullable=False, index=True)

    document_name = Column(String(255), nullable=False)

    document_type = Column(String(255),nullable=False)

    file_path = Column(String(255),nullable=False)

    uploaded_at = Column(DateTime(timezone=True),server_default=func.now())

    processed = Column(Integer, default=0)
