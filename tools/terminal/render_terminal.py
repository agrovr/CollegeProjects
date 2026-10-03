"""Replay a recording in xterm.js (headless Chromium) and save PNG frames.

    python tools/terminal/render_terminal.py demo.json frames/ --fps 8
    python tools/terminal/render_terminal.py demo.json stills/ --at 1200,4900

Needs Playwright for Python and xterm.js: run `npm install` in tools/terminal first. Set
XTERM_FONT to a .woff2 monospace font for consistent glyphs (JetBrains Mono is used for the
README media) and SCALE for the device pixel ratio (default 1).
"""

import asyncio
import base64
import json
import os
import sys

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
XTERM = os.path.join(HERE, "node_modules", "@xterm", "xterm")


async def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as handle:
        recording = json.load(handle)
    out, mode, value = sys.argv[2], sys.argv[3], sys.argv[4]
    os.makedirs(out, exist_ok=True)
    font = os.environ.get("XTERM_FONT", "")
    font_face = f"@font-face{{font-family:Capture;src:url(file://{font})}}" if font else ""
    page_html = os.path.join(out, "_page.html")
    with open(page_html, "w", encoding="utf-8") as handle:
        handle.write(f"""<html><head><link rel=stylesheet href="file://{XTERM}/css/xterm.css">
<style>{font_face} body{{margin:0;background:#18122a}} #t{{display:inline-block;padding:14px;background:#18122a}}</style>
<script src="file://{XTERM}/lib/xterm.js"></script></head><body><div id=t></div></body></html>""")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context(device_scale_factor=float(os.environ.get("SCALE", "1")),
                                            viewport={"width": 1600, "height": 1000})
        page = await context.new_page()
        await page.goto(f"file://{page_html}")
        await page.evaluate(f"""async () => {{
            if (document.fonts) {{ await document.fonts.load('16px Capture').catch(() => null); }}
            window.term = new Terminal({{cols: {recording['cols']}, rows: {recording['rows']},
                fontFamily: 'Capture, DejaVu Sans Mono, monospace', fontSize: 15, lineHeight: 1.0,
                theme: {{background: '#18122a', foreground: '#ece4f6'}}, customGlyphs: true}});
            term.open(document.getElementById('t'));
        }}""")

        if mode == "--at":
            times = [int(t) for t in value.split(",")]
        else:
            times = list(range(0, int(recording["duration"]), int(1000 / int(value))))
        chunks, index = recording["chunks"], 0
        for number, at in enumerate(times):
            data = b""
            while index < len(chunks) and chunks[index][0] <= at:
                data += base64.b64decode(chunks[index][1])
                index += 1
            if data:
                await page.evaluate(
                    "d => new Promise(r => term.write(Uint8Array.from(atob(d), c => c.charCodeAt(0)), r))",
                    base64.b64encode(data).decode())
            await page.wait_for_timeout(30)
            name = f"{at:06d}.png" if mode == "--at" else f"{number:04d}.png"
            await page.locator("#t").screenshot(path=os.path.join(out, name))
        await browser.close()
    os.remove(page_html)
    print(f"{len(times)} frames written to {out}")


if __name__ == "__main__":
    asyncio.run(main())
