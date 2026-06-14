"""文本生成服务"""

import torch

from . import config
from .model import load


def generate(prompt: str, max_new_tokens: int | None = None, temperature: float | None = None) -> str:
    model, tokenizer = load()
    max_new_tokens = max_new_tokens or config.MAX_NEW_TOKENS
    temperature = temperature if temperature is not None else config.TEMPERATURE

    messages = [{"role": "user", "content": prompt}]
    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    input_len = inputs["input_ids"].shape[1]

    print(inputs)
    print(inputs["input_ids"])

    print("---------------------------------------------------")

    print(generated_ids)

    print(tokenizer.decode(3323))
    print(tokenizer.decode(622))
    print(tokenizer.decode([3323, 622]))
    print(tokenizer.decode(29901))

    print("---------------------------------------------------")

    for id in inputs["input_ids"][0]:
        print(tokenizer.decode(id))
    return tokenizer.decode(generated_ids[0][input_len:], skip_special_tokens=True)
