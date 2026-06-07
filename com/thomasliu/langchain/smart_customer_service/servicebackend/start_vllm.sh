#!/bin/bash
# =========================================================
# 注意：本地 VL 模型已改用 transformers 直接加载（见 document_extractor.py）
# vLLM 与 RTX 2080 Ti (CC 7.5) 的 FlashInfer kernel 存在兼容问题
# 如需重新使用 vLLM，尝试安装兼容的 vLLM 版本或更换 GPU
# =========================================================
# 留空占位，模型由 app/rag/document_extractor.py 中的 _get_local_model() 惰性加载
echo "VL 模型由 transformers 直接加载，无需此服务。"
echo "见 app/rag/document_extractor.py 中的 _get_local_model()"
exit 0
