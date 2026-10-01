"""UI artifact builder for Unipalm.

The UI templates are independent from data extraction and intelligence logic.
This module only:
1) injects a payload into a template marker,
2) encrypts each UI artifact with the dashboard access key,
3) emits a dual-UI wrapper.

Default UI is V2. Add ?ui=v1 to the same production URL for immediate fallback.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DATA_MARKER="/*__UNIPALM_DATA__*/"


def inject_payload(template_text: str, payload: Dict[str,Any]) -> str:
    if template_text.count(DATA_MARKER) != 1:
        raise RuntimeError(f"template must contain exactly one {DATA_MARKER}")
    data="window.UNIPALM_DATA="+json.dumps(payload,ensure_ascii=False,separators=(",",":"))+";"
    return template_text.replace(DATA_MARKER,data,1)


def _encrypt_html(html: str, access_key: str, aad_text: str) -> Dict[str,Any]:
    salt=os.urandom(16)
    iv=os.urandom(12)
    iterations=210000
    aad=aad_text.encode("utf-8")
    key=hashlib.pbkdf2_hmac("sha256",access_key.encode("utf-8"),salt,iterations,32)
    cipher=AESGCM(key).encrypt(iv,gzip.compress(html.encode("utf-8"),9),aad)
    e=lambda x:base64.b64encode(x).decode("ascii")
    return {"s":e(salt),"i":e(iv),"n":iterations,"a":aad_text,"p":e(cipher)}


def build_dual_ui_wrapper(
    *,
    payload: Dict[str,Any],
    v2_template_path: Path,
    v1_template_path: Path,
    output_path: Path,
    access_key: str,
    build_id: str,
) -> Dict[str,Any]:
    v2=inject_payload(v2_template_path.read_text(encoding="utf-8"),payload)
    v1=inject_payload(v1_template_path.read_text(encoding="utf-8"),payload)
    enc2=_encrypt_html(v2,access_key,"unipalm-command-center-v2")
    enc1=_encrypt_html(v1,access_key,"unipalm-business-os-v1-fallback")

    wrapper=(
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="unipalm-build" content="{build_id}">'
        '<meta name="unipalm-ui-default" content="v2">'
        '<title>Unipalm Business OS</title></head><body>'
        '<div id="gate" style="font-family:Arial;max-width:440px;margin:15vh auto;padding:28px;border:1px solid #ddd;border-radius:20px">'
        '<h2 style="color:#045433">Unipalm Business OS</h2>'
        '<p>Dashboard nội bộ. Nhập khóa truy cập.</p>'
        '<input id="pw" type="password" style="width:100%;padding:12px;box-sizing:border-box">'
        '<button id="go" style="width:100%;margin-top:10px;padding:12px;background:#045433;color:#fff;border:0;border-radius:10px">Mở dashboard</button>'
        '<div id="mode" style="margin-top:12px;font-size:12px;color:#66716b"></div>'
        '<div id="msg" style="margin-top:8px;color:#b42318"></div></div>'
        '<iframe id="app" style="display:none;position:fixed;inset:0;width:100%;height:100%;border:0"></iframe>'
        f'<script id="p-v2" type="application/octet-stream">{enc2["p"]}</script>'
        f'<script id="p-v1" type="application/octet-stream">{enc1["p"]}</script>'
        '<script>'
        f'const META={{v2:{json.dumps({k:enc2[k] for k in ("s","i","n","a")},separators=(",",":"))},'
        f'v1:{json.dumps({k:enc1[k] for k in ("s","i","n","a")},separators=(",",":"))}}};'
        "const E=new TextEncoder(),B=s=>{const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u};"
        "const requested=new URLSearchParams(location.search).get('ui');"
        "const ui=requested==='v1'?'v1':'v2';"
        "mode.textContent=ui==='v1'?'Đang mở giao diện dự phòng V1 (?ui=v1)':'Command Center V2 · thêm ?ui=v1 vào URL nếu cần giao diện dự phòng';"
        "async function boot(){try{const m=META[ui],blob=document.getElementById('p-'+ui);"
        "const imported=await crypto.subtle.importKey('raw',E.encode(pw.value),'PBKDF2',false,['deriveKey']);"
        "const key=await crypto.subtle.deriveKey({name:'PBKDF2',salt:B(m.s),iterations:m.n,hash:'SHA-256'},imported,{name:'AES-GCM',length:256},false,['decrypt']);"
        "const q=await crypto.subtle.decrypt({name:'AES-GCM',iv:B(m.i),additionalData:E.encode(m.a)},key,B(blob.textContent.trim()));"
        "const h=await new Response(new Blob([q]).stream().pipeThrough(new DecompressionStream('gzip'))).text();"
        "app.onload=()=>{gate.style.display='none';app.style.display='block'};app.srcdoc=h"
        "}catch(e){msg.textContent='Khóa không đúng hoặc trình duyệt không hỗ trợ.'}}"
        "go.onclick=boot;pw.onkeydown=e=>{if(e.key==='Enter')boot()};"
        '</script></body></html>'
    )
    output_path.write_text(wrapper,encoding="utf-8")
    return {
        "defaultUi":"v2",
        "fallbackUi":"v1",
        "fallbackQuery":"?ui=v1",
        "output":str(output_path),
        "v2Bytes":len(v2.encode("utf-8")),
        "v1Bytes":len(v1.encode("utf-8")),
        "wrapperBytes":len(wrapper.encode("utf-8")),
    }
