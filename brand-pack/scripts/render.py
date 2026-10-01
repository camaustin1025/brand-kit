#!/usr/bin/env python3
"""
render.py - screenshots and SVG previews via headless Chrome. No Python dependencies.

Usage:
    python3 render.py page <url> --out <dir> [--width 1440] [--height 1100] [--mobile]
    python3 render.py svg <file.svg> --out <png-path> [--size 800] [--bg transparent|#ffffff|#111111]
    python3 render.py dom <url> --out <html-path>            # rendered DOM after JS, for JS-heavy sites

Prints one JSON line: {"status": "ok"|"skipped", ...}. Exit code 0 even when skipped, so the
skill can continue and record "visual check: skipped".
"""
import argparse
import base64
import re
import json
import os
import shutil
import subprocess
import sys
import tempfile

CHALLENGE = re.compile(r"(Just a moment|cf-chl|challenge-platform|Attention Required|Access denied|Verify you are human|"
                       r"Press (?:&|and|&amp;) Hold|Before we continue|not a bot|px-captcha|perimeterx|_px[A-Z]|hcaptcha|g-recaptcha|"
                       r"Pardon Our Interruption|Request unsuccessful|Incapsula|distil_r_captcha|bot detection)", re.I)

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Arc.app/Contents/MacOS/Arc",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
]


def find_chrome():
    env = os.environ.get("CHROME_PATH")
    if env and os.path.exists(env):
        return env
    for p in CHROME_PATHS:
        if os.path.isabs(p) and os.path.exists(p):
            return p
        w = shutil.which(p)
        if w:
            return w
    return None


def run_chrome(chrome, args, timeout=60, watch_file=None):
    """Run headless Chrome. Chrome's new headless mode often lingers after writing its output,
    so when watch_file is given, poll for it and kill Chrome once the file is stable."""
    import time
    profile = tempfile.mkdtemp(prefix="brandpack-chrome-")
    base = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            f"--user-data-dir={profile}", "--disable-features=TranslateUI",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"]
    if sys.platform.startswith("linux"):
        base.append("--no-sandbox")  # only needed when Chrome runs as root in a container; macOS and Windows keep the sandbox
    if "--dump-dom" in args:
        # Chrome prints the DOM and then lingers until the timeout. Write it to a file and stop as soon as </html> lands.
        out_path = os.path.join(profile, "dom.html")
        err_path = os.path.join(profile, "stderr.txt")
        with open(out_path, "w") as fo, open(err_path, "w") as fe:
            proc = subprocess.Popen(base + args, stdout=fo, stderr=fe)
            t0 = time.time()
            try:
                while time.time() - t0 < timeout and proc.poll() is None:
                    if os.path.getsize(out_path) > 500:
                        with open(out_path, "rb") as f:
                            f.seek(-64, os.SEEK_END)
                            if re.search(rb"</html>\s*$", f.read(), re.I):
                                break
                    time.sleep(0.25)
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
        out = open(out_path, encoding="utf-8", errors="replace").read()
        err = open(err_path, encoding="utf-8", errors="replace").read()
        shutil.rmtree(profile, ignore_errors=True)

        class D:  # minimal CompletedProcess stand-in
            pass
        r = D(); r.stdout, r.stderr, r.returncode = out, err, proc.returncode
        return r
    proc = subprocess.Popen(base + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t0 = time.time()
    out, err = "", ""
    try:
        if watch_file:
            last_size, stable_since = -1, None
            while time.time() - t0 < timeout:
                if proc.poll() is not None:
                    break
                if os.path.exists(watch_file):
                    sz = os.path.getsize(watch_file)
                    if sz > 500 and sz == last_size:
                        if stable_since and time.time() - stable_since > 1.5:
                            break
                        stable_since = stable_since or time.time()
                    else:
                        last_size, stable_since = sz, None
                time.sleep(0.25)
            if proc.poll() is None:
                proc.kill()
            try:
                out, err = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        else:
            out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    class R:  # minimal CompletedProcess stand-in
        pass
    r = R(); r.stdout, r.stderr, r.returncode = out or "", err or "", proc.returncode
    return r


def cmd_page(a, chrome):
    os.makedirs(a.out, exist_ok=True)
    shots = []
    sizes = [("desktop", a.width, a.height)]
    if a.mobile:
        sizes.append(("mobile", 390, 1200))
    for name, w, h in sizes:
        path = os.path.abspath(os.path.join(a.out, f"homepage-{name}.png"))
        if os.path.exists(path):
            os.remove(path)
        r = run_chrome(chrome, [f"--window-size={w},{h}", "--timeout=15000",
                                f"--screenshot={path}", a.url], watch_file=path)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            shots.append({"name": name, "path": path, "width": w, "height": h})
        else:
            shots.append({"name": name, "path": None, "error": (r.stderr or "")[-300:]})
    ok = [s for s in shots if s.get("path")]
    # detect bot walls: the screenshot exists but shows a challenge page, not the site
    challenge = None
    if ok:
        r = run_chrome(chrome, [f"--window-size={a.width},{a.height}", "--timeout=15000", "--dump-dom", a.url], timeout=45)
        dom = r.stdout or ""
        m = CHALLENGE.search(dom[:20000]) if dom else None
        if m or (dom and len(dom) < 3000):
            challenge = (m.group(0) if m else "near-empty document")
    if challenge:
        print(json.dumps({"status": "challenge", "reason": f"Bot challenge in headless Chrome ({challenge}). Screenshots show the challenge page, not the site. "
                                                             "Use a browser tool if one is available, else set visual_check.status to 'blocked'.",
                          "screenshots": shots}))
    else:
        print(json.dumps({"status": "ok" if ok else "skipped", "screenshots": shots}))


def svg_aspect(svg_bytes):
    import re
    txt = svg_bytes.decode("utf-8", errors="ignore")[:4000]
    vb = re.search(r"viewBox=[\"']\s*[\d.-]+[\s,]+[\d.-]+[\s,]+([\d.]+)[\s,]+([\d.]+)", txt)
    if vb and float(vb.group(1)) > 0:
        return float(vb.group(2)) / float(vb.group(1))
    w = re.search(r"\bwidth=[\"']([\d.]+)", txt)
    h = re.search(r"\bheight=[\"']([\d.]+)", txt)
    if w and h and float(w.group(1)) > 0:
        return float(h.group(1)) / float(w.group(1))
    return 0.5


def cmd_svg(a, chrome):
    """Render an SVG to PNG at the SVG's own aspect ratio, `size` px wide, with padding of 4%."""
    svg = open(a.svg, "rb").read()
    b64 = base64.b64encode(svg).decode("ascii")
    aspect = svg_aspect(svg)
    W = int(a.size)
    H = int(round(W * aspect))
    if H < 200:  # headless Chrome refuses very short windows; scale the render up instead of padding it
        W = int(round(200 / max(aspect, 0.01)))
        H = 200
    pad = int(W * 0.04)
    bg = "transparent" if a.bg == "transparent" else a.bg
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{{margin:0;background:{bg};}}
    body{{width:{W}px;height:{H}px;display:flex;align-items:center;justify-content:center;box-sizing:border-box;padding:{pad}px;}}
    img{{width:100%;height:100%;object-fit:contain;display:block;}}
    </style></head><body><img src="data:image/svg+xml;base64,{b64}"></body></html>"""
    tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(html)
    tmp.close()
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    extra = ["--default-background-color=00000000"] if a.bg == "transparent" else []
    if os.path.exists(out):
        os.remove(out)
    run_chrome(chrome, extra + [f"--window-size={W},{H}", "--timeout=5000",
                                f"--screenshot={out}", "file://" + tmp.name], watch_file=out)
    os.unlink(tmp.name)
    if os.path.exists(out) and os.path.getsize(out) > 500:
        print(json.dumps({"status": "ok", "png": out, "width": W, "height": H}))
    else:
        print(json.dumps({"status": "skipped", "reason": "chrome produced no file"}))


def cmd_dom(a, chrome):
    r = run_chrome(chrome, ["--window-size=1440,1100", "--timeout=15000", "--dump-dom", a.url], timeout=45)
    if r.stdout and len(r.stdout) > 500:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(r.stdout)
        print(json.dumps({"status": "ok", "html": os.path.abspath(a.out), "bytes": len(r.stdout)}))
    else:
        print(json.dumps({"status": "skipped", "reason": (r.stderr or "no output")[-300:]}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("page"); p.add_argument("url"); p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=1440); p.add_argument("--height", type=int, default=1100)
    p.add_argument("--mobile", action="store_true")
    s = sub.add_parser("svg"); s.add_argument("svg"); s.add_argument("--out", required=True)
    s.add_argument("--size", type=int, default=800); s.add_argument("--bg", default="transparent")
    d = sub.add_parser("dom"); d.add_argument("url"); d.add_argument("--out", required=True)
    a = ap.parse_args()
    chrome = find_chrome()
    if not chrome:
        print(json.dumps({"status": "skipped", "reason": "No Chrome/Chromium/Edge found. Set CHROME_PATH or use the browser tool for a screenshot."}))
        sys.exit(0)
    {"page": cmd_page, "svg": cmd_svg, "dom": cmd_dom}[a.cmd](a, chrome)


if __name__ == "__main__":
    main()
