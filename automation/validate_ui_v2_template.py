"""Static validation for the production Command Center V2 template."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=ROOT/"automation"/"command_center_v2_template.html"
MARKER="/*__UNIPALM_DATA__*/"


def main():
    html=TEMPLATE.read_text(encoding="utf-8")
    checks={
        "oneDataMarker": html.count(MARKER)==1,
        "noPreviewDependency": "command-center-preview-data.js" not in html,
        "noMockPeriods": "mockPeriods" not in html and "mockSignals" not in html and "mockDataSources" not in html,
        "embeddedLogo": "data:image/png;base64," in html,
        "scale125Preserved": "transform:scale(1.25)" in html,
        "sidebarPin": 'id="sidebarPin"' in html,
        "drawer": 'id="diagnosticDrawer"' in html and 'id="drawerBackdrop"' in html,
        "darkMode": '[data-theme="dark"]' in html,
        "productFeatureHealth": "productAdsMart" in html and "productIntelligence" in html,
        "noSellerOperatingHome": "Seller Operating Home" not in html,
        "contextualVietnameseCurrency": all(x in html for x in ('function moneyFull(v)','a>=1000000','+"tr đ"','value:moneyFull(cur.gmv)')),
        "fullCurrencyReservedForPrimaryCards": html.count('value:moneyFull(cur.gmv)')==1 and 'moneyWords(cur.gmv)' in html,
        "noEnglishCompactCurrency": all(x not in html for x in ('+"B"','+"M"','+"K"')),
        "aovVocabulary": 'return "AOV";' in html and "Giá trị đơn hàng trung bình" not in html,
        "operatorLanguage": all(x in html for x in ("Cơ sở phân tích","Chi tiêu Ads","Dữ liệu đạt chuẩn","Đã cập nhật đến","Lỗi dữ liệu lõi")),
        "noTechnicalStatusCopy": all(x not in html for x in ("Supporting signal","Data healthy","Loaded đến","DQ: core blocking","freshness + DQ threshold")),
    }
    errors=[k for k,v in checks.items() if not v]

    scripts=re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>",html,flags=re.I)
    with tempfile.TemporaryDirectory() as d:
        for idx,script in enumerate(scripts):
            if not script.strip():
                continue
            script=script.replace(MARKER,'window.UNIPALM_DATA={"commandCenter":{"status":"READY","periods":{},"labels":{},"featureHealth":{}}};')
            p=Path(d)/f"script_{idx}.js"
            p.write_text(script,encoding="utf-8")
            proc=subprocess.run(["node","--check",str(p)],capture_output=True,text=True)
            if proc.returncode:
                errors.append(f"jsSyntax[{idx}]: {proc.stderr.strip()}")

    print({"status":"PASS" if not errors else "FAIL","checks":checks,"errors":errors})
    if errors:
        raise SystemExit(1)


if __name__=="__main__":
    main()
