import os.path
import uuid

from fastapi import APIRouter, UploadFile, Depends, HTTPException
from fastapi.params import File, Form
from multipart import file_path
from sqlalchemy.orm import Session

from app.agent.memory import get_long_term_memory
from app.api.auth import get_current_user
from app.database.postgresql import get_postgres_db
from app.models.medical_document import MedicalDocument
from app.models.user import User
from app.rag.document_extractor import extract_medical_info_from_pdf, save_extracted_info_to_store

router = APIRouter()

UPLOAD_DIR = "./uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        document_type:str = Form(...),
        user_id:str = Form(...),
        current_user:User = Depends(get_current_user),
        db: Session = Depends(get_postgres_db)
):

    try:
        print(f"开始上传文档：{file.filename}, 用户：{user_id}")

        if not file.filename.endswith(('.pdf')):

            raise HTTPException(status_code=400, detail="文件类型错误")

        file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{uuid.uuid4().hex}_{file.filename}")

        with open(file_path, "wb") as f:
            content = await file.read()

            f.write(content)

        print(f"文件保存成功 :{file_path}")

        record = extract_medical_info_from_pdf(file_path)

        store = get_long_term_memory()

        saved_items = save_extracted_info_to_store(store=store, user_id=user_id, record=record, filename=file.filename,)

        db_document = MedicalDocument(
            user_id=user_id,
            document_type=document_type,
            file_path=file_path,
            document_name=file.filename,
            processed=1
        )

        db.add(db_document)

        db.commit()

        db.refresh(db_document)

        return {
            "message": "文档上传成功,信息已提取并保存",
            "document_id": db_document.id,
            "extracted_items": saved_items,
            "total_items": len(saved_items)
        }

    except Exception as e:
        print(f"文档上传失败{str(e)}")
        raise HTTPException(status_code=500, detail="文档上传失败")