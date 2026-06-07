import json
import re
from typing import Any, Optional

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from pdf2image import convert_from_path
from PIL import Image

from app.config.settings import settings

MEDICAL_OCR_PROMPT = (
    "你是一个医疗文档 OCR 专家。请提取此医疗文档页面上的所有可见文字。"
    "包括：患者姓名、年龄、性别、症状描述、诊断结果、用药记录、检查结果、医嘱等。"
    "保持原文语言和格式。尽可能完整。"
)

MEDICAL_EXTRACTOR_PROMPT = """你是专业的医疗信息提取专家，从医疗文档中提取关键信息。
【必须提取的字段】
1. basic_info（基本信息）- 必须提取！包含：
   - name: 患者姓名（字符串）
   - age: 年龄（整数或字符串，如"30"或"30岁"）
   - gender: 性别（男/女）
   - phone: 联系电话（字符串，如"13812345678"）
   - email: 电子邮箱（字符串，如"zhangsan@example.com"）
   - address: 家庭地址（字符串）
   - id_card: 身份证号（字符串）
   注意：如果文档中有这些信息，必须提取；如果没有，可以省略该字段

2. symptoms（症状）- 症状列表，每项可以是字符串或对象
3. medical_history（既往病史）- 历史疾病列表
4. allergies（过敏史）- 过敏药物或食物列表
5. diagnoses（诊断结果）- 医生诊断列表
6. medications（用药记录）- 当前或历史用药列表
7. test_results（检查结果）- 化验/检查结果列表
8. doctor_notes（医生备注）- 其他备注（字符串或列表）

【提取规则】
1. 只提取文档中明确提到的信息，不要臆测或编造
2. 如果文档中有患者姓名、年龄、性别、电话、邮箱、地址等，必须填入 basic_info
3. 如果某类信息确实不存在，返回空列表 [] 或 null
4. 保持原文表述，不要改写
5. 必须返回符合 JSON 格式的结果"""

class MedicalRecord(BaseModel):
    basic_info: Optional[dict] = Field(default_factory=dict, description="基本信息对象")
    symptoms: Any = Field(default_factory=list, description="症状列表")
    medical_history: Any = Field(default_factory=list, description="既往病史列表")
    allergies: Any = Field(default_factory=list, description="过敏史列表")
    diagnoses: Any = Field(default_factory=list, description="诊断结果列表")
    medications: Any = Field(default_factory=list, description="用药记录列表")
    test_results: Any = Field(default_factory=list, description="检查结果列表")
    doctor_notes: Any = Field(default_factory=list, description="医生备注列表")

_parser = PydanticOutputParser(pydantic_object=MedicalRecord)

# ─── 全局惰性加载（单例模式，复用模型） ───
_llm = None
_processor = None

def _get_local_model():
    global _llm, _processor
    if _llm is None:
        import torch
        from transformers import AutoProcessor

        model_path = settings.VL_MODEL_PATH
        with open(f"{model_path}/config.json") as f:
            archs = json.load(f).get("architectures", [])

        if "Qwen2_5_VL" in str(archs):
            from transformers import Qwen2_5_VLForConditionalGeneration as ModelClass
        else:
            from transformers import AutoModelForCausalLM as ModelClass

        print(f"加载本地 VL 模型: {model_path}")
        _llm = ModelClass.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        _processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        print(f"模型加载完成，设备: {_llm.device}")
    return _llm, _processor

def _extract_json(text: str) -> dict:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end+1]
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        text = re.sub(r"(?<!\\)\\(?![nrtbf\\\"'/]|u[0-9a-fA-F]{4})", "", text)
        return json.loads(text)
    except json.JSONDecodeError:
        return {}

# ─── PDF 转图片 ───

def pdf_to_images(pdf_path: str, dpi: int = 150, max_size: int = 1280) -> list[Image.Image]:
    images = convert_from_path(pdf_path, dpi=dpi)
    result = []
    for img in images:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        result.append(img)
    print(f"PDF 转图片成功，共 {len(result)} 页")
    return result

# ─── OCR 识别单页 ───

def ocr_page(image: Image.Image) -> str:
    model, processor = _get_local_model()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": MEDICAL_OCR_PROMPT},
            ],
        }
    ]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    generated_ids = model.generate(**inputs, max_new_tokens=2048, temperature=0.1)
    input_len = inputs["input_ids"].shape[1]
    response = processor.decode(generated_ids[0][input_len:], skip_special_tokens=True)
    return response.strip()

# ─── 从文本提取结构化医疗信息 ───

def extract_medical_info(text: str) -> MedicalRecord:
    model, processor = _get_local_model()
    format_instructions = _parser.get_format_instructions()
    user_prompt = f"请从以下医疗文档中提取信息：\n\n{text[:8000]}"
    system_prompt = f"{MEDICAL_EXTRACTOR_PROMPT}\n\n{format_instructions}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    input_text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(input_text, return_tensors="pt").to(model.device)
    generated_ids = model.generate(
        **inputs,
        max_new_tokens=2048,
        temperature=0.1,
        do_sample=True,
        pad_token_id=processor.tokenizer.pad_token_id or processor.tokenizer.eos_token_id,
    )
    input_len = inputs["input_ids"].shape[1]
    response = processor.decode(
        generated_ids[0][input_len:], skip_special_tokens=True
    ).strip()

    print(f"提取输出: {response[:200]}...")

    parsed = _extract_json(response)
    if parsed:
        return MedicalRecord(**parsed)
    print("JSON 解析失败，返回空记录")
    return MedicalRecord()

# ─── 主入口：PDF → 图片 → OCR → 结构化提取 ───

def extract_medical_info_from_pdf(file_path: str) -> MedicalRecord:
    try:
        print(f"开始处理 PDF: {file_path}")

        images = pdf_to_images(file_path)
        ocr_texts = []
        for i, img in enumerate(images):
            print(f"  OCR 第 {i+1}/{len(images)} 页...")
            page_text = ocr_page(img)
            ocr_texts.append(f"--- 第 {i+1} 页 ---\n{page_text}")

        full_text = "\n\n".join(ocr_texts)
        print(f"OCR 完成，共 {len(full_text)} 字符")

        return extract_medical_info(full_text)

    except Exception as e:
        import traceback
        print(f"信息提取出错: {e}")
        traceback.print_exc()
        return MedicalRecord()


def save_extracted_info_to_store(store, user_id: str, record: MedicalRecord, filename: str) -> list:
    save_items = []

    if record.basic_info:
        basic_text = ",".join([f"{k}:{v}" for k, v in record.basic_info.items() if v is not None])
        namespace = ("user_preferences", user_id)
        store.put(namespace, f"basic_{filename}", {
            "key": "基本信息",
            "value": basic_text,
            "source": f"文档:{filename}",
        })
        print("已保存用户信息到长记忆")
        save_items.append(f"基本信息: {basic_text}")

    medical_parts = []
    medical_fields = {
        "symptoms": ("症状", record.symptoms),
        "medical_history": ("既往病史", record.medical_history),
        "allergies": ("过敏史", record.allergies),
        "diagnoses": ("诊断结果", record.diagnoses),
        "medications": ("用药记录", record.medications),
        "test_results": ("检查结果", record.test_results),
        "doctor_notes": ("医生备注", record.doctor_notes),
    }

    for field_label, items in medical_fields.values():
        if items:
            if isinstance(items, str):
                items = [items]
            elif not isinstance(items, list):
                items = []
            content = ";".join([str(item) for item in items if item is not None])
            medical_parts.append(f"{field_label}:{content}")

    if medical_parts:
        medical_text = "\n".join(medical_parts)
        namespace = ("user_medical_history", user_id)
        store.put(namespace, f"medical_{filename}", {
            "category": "医疗信息",
            "content": medical_text,
            "source": f"文档:{filename}",
        })
        print("已保存医疗信息到长记忆")
        save_items.append(f"医疗信息: {medical_text[:100]}...")

    return save_items
