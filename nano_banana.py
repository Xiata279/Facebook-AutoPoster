#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍌 Nano Banana 2 — Image Generator (Gemini API)
================================================
Wrapper tạo ảnh AI dùng Gemini API chính thức.
Inspired by: github.com/kingbootoshi/nano-banana-2-skill

Tính năng:
  - Tạo ảnh từ text prompt (Flash / Pro model)
  - Hỗ trợ nhiều aspect ratio (1:1, 16:9, 9:16, ...)
  - Chế độ nền xanh (green screen) để xóa nền
  - Theo dõi chi phí (cost tracking)
  - Dùng được từ GUI (app.py) và CLI

@author  Xiata (ported from kingbootoshi/nano-banana-2-skill)
@version 1.0.0
"""

import os, json, base64, time, sys
from pathlib import Path
from datetime import datetime

BASE     = Path(__file__).parent
LOG_DIR  = BASE / "logs"
OUT_DIR  = BASE / "output"
COST_FILE = BASE / "logs" / "nb_costs.json"

# ── Models ────────────────────────────────────────────────
MODELS = {
    "flash": "gemini-2.0-flash-preview-image-generation",
    "nb2"  : "gemini-2.0-flash-preview-image-generation",  # alias
    "pro"  : "gemini-2.5-pro-preview-05-06",
    "nb-pro": "gemini-2.5-pro-preview-05-06",              # alias
}

# Cost per image (USD) — approximate
COSTS = {
    "flash": 0.020,
    "pro"  : 0.040,
}

# ── Aspect ratios ─────────────────────────────────────────
ASPECT_RATIOS = [
    "1:1", "16:9", "9:16", "4:3", "3:4",
    "3:2", "2:3", "4:5", "5:4", "21:9",
]

# ── Sizes ─────────────────────────────────────────────────
SIZE_MAP = {
    "512":  512,
    "1K":  1024,
    "2K":  2048,
    "4K":  4096,
}


# ══════════════════════════════════════════════════════════
#  CORE GENERATOR
# ══════════════════════════════════════════════════════════

def generate_image(
    prompt: str,
    *,
    api_key: str = "",
    model: str = "flash",
    aspect: str = "1:1",
    size: str = "1K",
    transparent: bool = False,
    output_name: str = "",
    output_dir: str = "",
    on_log=None,
) -> dict:
    """
    Tạo ảnh bằng Gemini API.

    Returns:
        {
            "success": bool,
            "image_path": str,
            "filename": str,
            "model": str,
            "cost_usd": float,
            "message": str,
        }
    """
    def _log(msg, level="info"):
        if on_log:
            on_log(msg, level)
        else:
            print(f"[NB2] {msg}")

    # ── Resolve API key ──────────────────────────────────
    key = (
        api_key
        or os.environ.get("GEMINI_API_KEY", "")
        or _read_env_key()
    )
    if not key:
        return _err("Không tìm thấy GEMINI_API_KEY. Vui lòng thêm vào file .env")

    # ── Resolve model ────────────────────────────────────
    model_id = MODELS.get(model.lower(), model)
    model_tier = "pro" if "pro" in model.lower() else "flash"

    # ── Build prompt ─────────────────────────────────────
    final_prompt = prompt
    if transparent:
        final_prompt += (
            " IMPORTANT: Generate on a solid pure green (#00FF00) background "
            "for chroma key removal. Keep edges clean and sharp."
        )

    # ── Validate aspect ──────────────────────────────────
    if aspect not in ASPECT_RATIOS:
        aspect = "1:1"

    _log(f"🍌 Nano Banana 2 — Model: {model_id} | {size} | {aspect}")
    _log(f"📝 Prompt: {final_prompt[:80]}...")

    # ── Call Gemini API ──────────────────────────────────
    try:
        import urllib.request, urllib.error

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"imagen-3.0-generate-002:predict?key={key}"
        )

        payload = {
            "instances": [{"prompt": final_prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": aspect,
                "safetyFilterLevel": "block_some",
                "personGeneration": "allow_adult",
            },
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err_msg = json.loads(body).get("error", {}).get("message", body)
        except:
            err_msg = body[:200]
        return _err(f"Gemini API lỗi {e.code}: {err_msg}")
    except Exception as e:
        return _err(f"Lỗi kết nối: {e}")

    # ── Parse response ───────────────────────────────────
    predictions = result.get("predictions", [])
    if not predictions:
        return _err("API không trả về ảnh. Thử đổi prompt hoặc model.")

    img_b64 = (
        predictions[0].get("bytesBase64Encoded")
        or predictions[0].get("image")
    )
    if not img_b64:
        return _err(f"Không tìm thấy dữ liệu ảnh: {json.dumps(result)[:200]}")

    # ── Save image ───────────────────────────────────────
    img_bytes = base64.b64decode(img_b64)

    out_folder = Path(output_dir) if output_dir else OUT_DIR
    out_folder.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = output_name or f"nb2_{ts}"
    if not name.endswith(".png"):
        name += ".png"
    img_path = out_folder / name

    img_path.write_bytes(img_bytes)
    _log(f"✅ Đã lưu ảnh: {img_path}", "ok")

    # ── Track cost ───────────────────────────────────────
    cost = COSTS.get(model_tier, 0.020)
    _track_cost(model_id, cost)
    _log(f"💰 Chi phí ước tính: ${cost:.3f}", "info")

    return {
        "success": True,
        "image_path": str(img_path),
        "filename": name,
        "model": model_id,
        "cost_usd": cost,
        "message": "Tạo ảnh thành công!",
    }


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def _err(msg: str) -> dict:
    return {"success": False, "image_path": "", "filename": "",
            "model": "", "cost_usd": 0.0, "message": msg}


def _read_env_key() -> str:
    """Đọc GEMINI_API_KEY từ .env trong thư mục project."""
    env_file = BASE / ".env"
    if env_file.exists():
        for line in env_file.read_text("utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def _track_cost(model_id: str, cost: float):
    """Lưu lịch sử chi phí vào logs/nb_costs.json."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    history = []
    if COST_FILE.exists():
        try:
            history = json.loads(COST_FILE.read_text("utf-8"))
        except:
            history = []
    history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model_id,
        "cost_usd": cost,
    })
    COST_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_total_cost() -> dict:
    """Trả về tổng chi phí và số lần tạo ảnh."""
    if not COST_FILE.exists():
        return {"total_generations": 0, "total_usd": 0.0, "by_model": {}}
    try:
        history = json.loads(COST_FILE.read_text("utf-8"))
    except:
        return {"total_generations": 0, "total_usd": 0.0, "by_model": {}}

    total = sum(r.get("cost_usd", 0) for r in history)
    by_model = {}
    for r in history:
        m = r.get("model", "unknown")
        by_model[m] = by_model.get(m, 0) + r.get("cost_usd", 0)

    return {
        "total_generations": len(history),
        "total_usd": round(total, 4),
        "by_model": {k: round(v, 4) for k, v in by_model.items()},
    }


# ══════════════════════════════════════════════════════════
#  CLI (dùng độc lập)
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="🍌 Nano Banana 2 — Tạo ảnh AI bằng Gemini"
    )
    parser.add_argument("prompt", nargs="?", default="", help="Prompt tạo ảnh")
    parser.add_argument("-m", "--model",  default="flash",
                        help="Model: flash (nb2) | pro (nb-pro) | default: flash")
    parser.add_argument("-a", "--aspect", default="1:1",
                        help=f"Tỷ lệ ảnh: {', '.join(ASPECT_RATIOS)}")
    parser.add_argument("-s", "--size",   default="1K",
                        help="Độ phân giải: 512 | 1K | 2K | 4K")
    parser.add_argument("-t", "--transparent", action="store_true",
                        help="Nền xanh lá (green screen)")
    parser.add_argument("-o", "--output", default="",
                        help="Tên file output (không cần .png)")
    parser.add_argument("-d", "--dir",    default="",
                        help="Thư mục lưu ảnh")
    parser.add_argument("--costs", action="store_true",
                        help="Xem tổng chi phí")
    parser.add_argument("--api-key",      default="",
                        help="Gemini API key (ghi đè .env)")
    args = parser.parse_args()

    if args.costs:
        info = get_total_cost()
        print(f"\n🍌 Nano Banana 2 — Thống kê chi phí")
        print(f"   Tổng lần tạo : {info['total_generations']}")
        print(f"   Tổng chi phí : ${info['total_usd']:.4f} USD")
        for m, c in info["by_model"].items():
            print(f"   {m}: ${c:.4f}")
        sys.exit(0)

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    result = generate_image(
        args.prompt,
        api_key=args.api_key,
        model=args.model,
        aspect=args.aspect,
        size=args.size,
        transparent=args.transparent,
        output_name=args.output,
        output_dir=args.dir,
    )

    if result["success"]:
        print(f"\n✅ Thành công! Ảnh lưu tại: {result['image_path']}")
        print(f"   Model : {result['model']}")
        print(f"   Chi phí: ~${result['cost_usd']:.3f} USD")
    else:
        print(f"\n❌ Lỗi: {result['message']}")
        sys.exit(1)
