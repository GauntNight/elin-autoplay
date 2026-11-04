"""Capture the Elin window's own pixels to a PNG. Read-only.

Uses PrintWindow(PW_CLIENTONLY | PW_RENDERFULLCONTENT) on the Elin window
handle, so it works while the game is behind other windows and can never
record a window lying on top of it. Never replace this with a screen-region
grab (ImageGrab.grab(bbox=...)): that captured another app's content on
2026-10-15.

usage: python -I tools/elin_eye.py [out.png] [--width N]
  --width N  downscale to N px wide (default 1600; 0 = full size)
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "runs" / "captures" / "latest.png"


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


def find_elin():
    hwnd = ctypes.windll.user32.FindWindowW(None, "Elin")
    if not hwnd:
        sys.exit("Elin window not found (is the game running?)")
    return hwnd


def capture(hwnd):
    u, g = ctypes.windll.user32, ctypes.windll.gdi32
    if u.IsIconic(hwnd):
        sys.exit("Elin is minimized; PrintWindow returns nothing useful")
    r = wt.RECT()
    u.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.right, r.bottom
    hdc = u.GetDC(hwnd)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, h)
    g.SelectObject(mdc, bmp)
    try:
        if not u.PrintWindow(hwnd, mdc, 1 | 2):  # PW_CLIENTONLY | PW_RENDERFULLCONTENT
            sys.exit("PrintWindow failed")
        bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(w * h * 4)
        g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    finally:
        g.DeleteObject(bmp)
        g.DeleteDC(mdc)
        u.ReleaseDC(hwnd, hdc)
    return Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(DEFAULT_OUT))
    ap.add_argument("--width", type=int, default=1600)
    a = ap.parse_args()
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    img = capture(find_elin())
    full = img.size
    if a.width and img.width > a.width:
        img = img.resize((a.width, round(img.height * a.width / img.width)), Image.LANCZOS)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"{out}  full={full[0]}x{full[1]}  saved={img.width}x{img.height}  "
          f"scale={full[0] / img.width:.3f}")


if __name__ == "__main__":
    main()
