"""模型加载（惰性单例）"""

import json
import os

from transformers import AutoTokenizer

from . import config

_llm = None
_tokenizer = None


def _get_model_class():
    with open(os.path.join(config.MODEL_PATH, "config.json")) as f:
        archs = json.load(f).get("architectures", [])
    if "Qwen2_5_VL" in str(archs):
        from transformers import Qwen2_5_VLForConditionalGeneration as M
    else:
        from transformers import AutoModelForCausalLM as M
    return M


def load():
    global _llm, _tokenizer
    if _llm is not None:
        return _llm, _tokenizer

    print(f"加载模型: {config.MODEL_PATH}")
    model_cls = _get_model_class()

    _llm = model_cls.from_pretrained(
        config.MODEL_PATH,
        device_map=config.DEVICE,
        torch_dtype=config.DTYPE,
        attn_implementation="eager",
    )
    _tokenizer = AutoTokenizer.from_pretrained(config.MODEL_PATH)
    print(f"模型加载完成，设备: {_llm.device}")
    return _llm, _tokenizer
