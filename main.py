#!/usr/bin/env python3
"""
策略 API：带签名的 POST 测试（与 backend-server internal/server/gin/middleware.go
CollectParamsAndBodyForSign + verifySignatureWithParams 对齐）。

- 请求头：X-MBX-APIKEY = 策略 API Key（公钥）
- Secret：策略 API Secret，仅用于本地计算 HMAC-SHA256
- 签名字符串：query 参数键值对 + JSON 顶层键值对（去掉 signature），
  再按 key 字典序 urlencode；布尔为 true/false；HMAC-SHA256 后十六进制小写。

环境变量（可选）：
  STRATEGY_API_KEY, STRATEGY_API_SECRET, STRATEGY_API_BASE_URL
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple
from urllib.parse import urlencode


def _format_float_go_style(x: float) -> str:
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("invalid float for signing")
    s = f"{x:.15f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def scalar_to_string(v: Any) -> str | None:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return _format_float_go_style(v)
    if isinstance(v, str):
        return v
    if v is None:
        return "<nil>"
    return None


def flatten_json_for_sign(obj: Dict[str, Any]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for key, v in obj.items():
        if key.lower() == "signature":
            continue
        s = scalar_to_string(v)
        if s is not None:
            pairs.append((key, s))
        else:
            pairs.append((key, json.dumps(v, ensure_ascii=False, separators=(",", ":"))))
    return pairs


def go_style_encode(pairs: List[Tuple[str, str]]) -> str:
    return urlencode(sorted(pairs, key=lambda kv: kv[0]), doseq=True)


def sign_payload(secret: str, pairs: List[Tuple[str, str]]) -> str:
    qs = go_style_encode(pairs)
    mac = hmac.new(secret.encode("utf-8"), qs.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def build_signed_body(
    secret: str,
    fields: Dict[str, Any],
    extra_query: List[Tuple[str, str]] | None = None,
    timestamp_ms: int | None = None,
) -> Dict[str, Any]:
    body = dict(fields)
    body["timestamp"] = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)

    pairs = list(extra_query or []) + flatten_json_for_sign(body)
    body["signature"] = sign_payload(secret, pairs)
    return body


def post_json(url: str, api_key: str, body: Dict[str, Any]) -> Tuple[int, str]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-MBX-APIKEY": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, raw


def main() -> None:
    ap = argparse.ArgumentParser(description="策略 API 签名 POST（创建母单）")
    ap.add_argument(
        "--base-url",
        default=os.environ.get("STRATEGY_API_BASE_URL", "http://127.0.0.1:8000"),
        help="服务根 URL，无末尾斜杠",
    )
    ap.add_argument("--api-key", default=os.environ.get("STRATEGY_API_KEY", ""))
    ap.add_argument("--secret", default=os.environ.get("STRATEGY_API_SECRET", ""))
    ap.add_argument("--dry-run", action="store_true", help="只打印签名与 body，不请求")
    args = ap.parse_args()

    if not args.api_key or not args.secret:
        ap.error("请提供 --api-key / --secret 或环境变量 STRATEGY_API_KEY / STRATEGY_API_SECRET")

    url = args.base_url.rstrip("/") + "/user/trading/master-orders"

    order_fields: Dict[str, Any] = {
        "algorithm": "TWAP",
        "exchange": "Binance",
        "symbol": "ETHUSDC",
        "marketType": "SPOT",
        "side": "sell",
        "totalQuantity": 0.0656,
        "strategyType": "TWAP-1",
        "executionDurationSeconds": 40,
        "mustComplete": True,
        "apiKeyId": "0b057efbbcea46db885ae66c98d20849",
        "clientOrderId": f"PY-{int(time.time() * 1000)}",
    }

    body = build_signed_body(args.secret, order_fields)
    pre_sig_pairs = list(flatten_json_for_sign({k: v for k, v in body.items() if k != "signature"}))
    print("sign string (no signature key):\n", go_style_encode(pre_sig_pairs), "\n", sep="")
    print("signature:", body["signature"])

    if args.dry_run:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return

    code, text = post_json(url, args.api_key, body)
    print("HTTP", code)
    print(text)


if __name__ == "__main__":
    main()