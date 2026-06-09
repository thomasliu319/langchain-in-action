"""
HuggingFace 模型下载工具
从 hf-mirror.com 下载模型到 /home/thomas/Downloads/models
顺序下载，独占带宽，支持断点续传，显示下载进度

用法:
  python download_model.py                              # 默认 Qwen2.5-VL-7B-Instruct
  python download_model.py Qwen/Qwen3-Embedding-0.6B
  python download_model.py --ignore *.ot *.onnx
"""
import os
import sys
import time
import math
import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

BASE_DIR = "/home/thomas/Downloads/models"
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
HF_TOKEN = os.getenv("HF_TOKEN", "")

HEADERS = {"User-Agent": "hf-download-tool"}
if HF_TOKEN:
    HEADERS["Authorization"] = f"Bearer {HF_TOKEN}"

BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{rate_fmt}, {percentage:.0f}%]"


def get_file_list(repo_id: str) -> list[dict]:
    api_url = f"{HF_ENDPOINT}/api/models/{repo_id}/tree/main"
    resp = requests.get(api_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    files = []
    for f in resp.json():
        if f["type"] == "file":
            files.append({"path": f["path"], "size": f["size"]})
    return sorted(files, key=lambda x: x["size"])


def download(repo_id: str, file_path: str, local_path: str, file_size: int,
             pbar: tqdm | None = None) -> bool:
    if os.path.exists(local_path) and os.path.getsize(local_path) == file_size:
        tqdm.write(f"  ✓ {file_path}")
        if pbar:
            pbar.update(file_size)
        return True

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    existing = os.path.getsize(local_path) if os.path.exists(local_path) else 0

    if existing > 0:
        tqdm.write(f"  ↻ {file_path}  续传 {_fmt(existing)}/{_fmt(file_size)}")
    else:
        tqdm.write(f"  ↓ {file_path}")

    headers = dict(HEADERS)
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"

    url = f"{HF_ENDPOINT}/{repo_id}/resolve/main/{file_path}"

    for attempt in range(10):
        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=30)
            resp.raise_for_status()
            mode = "ab" if existing > 0 else "wb"
            total = file_size - existing if existing > 0 else file_size
            local_pbar = tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=f"  {file_path[:50]:50s}",
                bar_format=BAR_FORMAT,
                leave=False,
            )
            with open(local_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=16 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        local_pbar.update(len(chunk))
            local_pbar.close()
            break
        except (requests.ConnectionError, requests.Timeout) as e:
            tqdm.write(f"     中断，5秒后重试 ({attempt+1}/10)...")
            time.sleep(5)
            if os.path.exists(local_path):
                headers["Range"] = f"bytes={os.path.getsize(local_path)}-"

    actual = os.path.getsize(local_path) if os.path.exists(local_path) else 0
    if actual == file_size:
        tqdm.write(f"  ✓ {file_path}")
        if pbar:
            pbar.update(file_size)
        return True
    else:
        tqdm.write(f"     未完成 ({_fmt(actual)}/{_fmt(file_size)})，下次自动续传")
        return False


def download_repo(repo_id: str, ignore_patterns: list[str] | None = None):
    local_dir = os.path.join(BASE_DIR, repo_id.split("/")[-1])

    print(f"模型: {repo_id}")
    print(f"镜像: {HF_ENDPOINT}")
    print(f"Token: {'已设置' if HF_TOKEN else '未设置'}")
    print(f"保存: {local_dir}")
    print()

    files = get_file_list(repo_id)
    ignore = ignore_patterns or []
    files = [
        f for f in files
        if not any(f["path"].endswith(p.lstrip("*.")) or f["path"] == p
                   for p in ignore)
    ]

    total = sum(f["size"] for f in files)
    print(f"文件数: {len(files)}, 总计: {_fmt(total)}")
    print()

    overall = tqdm(total=total, unit="B", unit_scale=True,
                   desc="总体进度", bar_format=BAR_FORMAT)

    done = 0
    for f in files:
        local_path = os.path.join(local_dir, f["path"])
        if download(repo_id, f["path"], local_path, f["size"], overall):
            done += 1

    overall.close()
    print(f"\n{'='*40}")
    print(f"完成: {done}/{len(files)} 个文件 ({_fmt(sum(f['size'] for f in files))})")
    if done < len(files):
        print("重新运行脚本会自动续传未完成文件")


def _fmt(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "microsoft/Phi-3-mini-4k-instruct"
    download_repo(model)
