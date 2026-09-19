#!/usr/bin/env python3
"""
Builds a cyberpunk "glitch" version of a GitHub avatar as an animated SVG.

How the effect works:
  * The avatar is embedded once (base64) and reused with <use>, so the file stays small.
  * RGB split: during a glitch burst the normal image fades out and two copies take over,
    one showing only the red channel, one only green+blue (cyan). They are blended with
    "screen", which adds them back into the full-colour picture, so when they sit exactly
    on top of each other it looks normal, and when they are pulled apart you get the
    red/cyan fringing.
  * Slices: horizontal bands of the image are clipped out and jerked sideways.
  * Scanlines + a rotating neon ring give the HUD feel.
Everything is plain CSS keyframes inside the SVG, which GitHub renders in <img> tags.

Usage:
  python glitch_avatar.py --user JiroRaiden --out dist/glitch-avatar.svg
  python glitch_avatar.py --image local.png --out test.svg      # for local testing
Only uses the Python standard library, so it runs on a bare GitHub Actions runner.
"""
import argparse
import base64
import urllib.request

SIZE = 420
C = SIZE / 2          # centre
R = 165               # avatar radius

PINK = "#ff2a6d"
CYAN = "#05d9e8"
PURPLE = "#7700ff"


def load_image(user=None, path=None):
    if path:
        data = open(path, "rb").read()
    else:
        url = f"https://github.com/{user}.png?size=400"
        req = urllib.request.Request(url, headers={"User-Agent": "glitch-avatar"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    # sniff the format from the file signature
    mime = "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(data).decode()


# Horizontal bands that get sliced sideways: (y, height, animation name, delay)
SLICES = [
    (C - R + 40, 22, "sliceA", "0s"),
    (C - 30, 14, "sliceB", "0s"),
    (C + 25, 30, "sliceC", "0s"),
    (C + R - 70, 12, "sliceB", "0.05s"),
]


def build_svg(href):
    x0 = C - R
    slice_clips = "\n".join(
        f'    <clipPath id="band{i}"><rect x="0" y="{y}" width="{SIZE}" height="{h}"/></clipPath>'
        for i, (y, h, _, _) in enumerate(SLICES)
    )
    tint = ['', ' filter="url(#cyanOnly)"']   # every other slice is tinted cyan
    slice_layers = "\n".join(
        f'  <g clip-path="url(#band{i})"><g style="animation-name:{name};animation-delay:{d}" class="slice">'
        f'<use href="#av"{tint[i % 2]}/></g></g>'
        for i, (y, h, name, d) in enumerate(SLICES)
    )
    bars = "\n".join(
        f'  <rect class="bar" x="{C - R - 10}" y="{y + h / 2 - 1}" width="{2 * R + 20}" height="2" '
        f'fill="{PINK if i % 2 else CYAN}" style="animation-delay:{d}"/>'
        for i, (y, h, _, d) in enumerate(SLICES)
    )

    def bracket(x, y, dx, dy):
        return (f'<path d="M{x} {y + 26 * dy} L{x} {y} L{x + 26 * dx} {y}" '
                f'stroke="{CYAN}" stroke-width="3" fill="none"/>')

    brackets = "".join([
        bracket(12, 12, 1, 1), bracket(SIZE - 12, 12, -1, 1),
        bracket(12, SIZE - 12, 1, -1), bracket(SIZE - 12, SIZE - 12, -1, -1),
    ])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" width="{SIZE}" height="{SIZE}">
  <style>
    /* one 6s loop: a hard glitch burst at the start, a small twitch in the middle, calm otherwise */
    .base  {{ animation: baseFade 6s steps(1, end) infinite; }}
    .red   {{ mix-blend-mode: screen; animation: redShift 6s steps(1, end) infinite; opacity: 0; }}
    .cyan  {{ mix-blend-mode: screen; animation: cyanShift 6s steps(1, end) infinite; opacity: 0; }}
    .slice {{ opacity: 0; animation-duration: 6s; animation-timing-function: steps(1, end); animation-iteration-count: infinite; }}
    .bar   {{ animation: bar 6s steps(1, end) infinite; opacity: 0; }}
    .ring1 {{ transform-origin: {C}px {C}px; animation: spin 14s linear infinite; }}
    .ring2 {{ transform-origin: {C}px {C}px; animation: spin 22s linear infinite reverse; }}
    .scan  {{ animation: scan 4s linear infinite; }}
    .glow  {{ animation: pulse 3s ease-in-out infinite; }}

    @keyframes baseFade {{
      0% {{ opacity: 0 }} 9% {{ opacity: 1 }} 55% {{ opacity: 0 }} 58% {{ opacity: 1 }}
    }}
    @keyframes redShift {{
      0%  {{ opacity: 1; transform: translate(-9px, 0) }}
      3%  {{ opacity: 1; transform: translate(6px, 2px) }}
      6%  {{ opacity: 1; transform: translate(-4px, -1px) }}
      9%  {{ opacity: 0; transform: none }}
      55% {{ opacity: 1; transform: translate(-5px, 0) }}
      58% {{ opacity: 0; transform: none }}
    }}
    @keyframes cyanShift {{
      0%  {{ opacity: 1; transform: translate(9px, 0) }}
      3%  {{ opacity: 1; transform: translate(-6px, -2px) }}
      6%  {{ opacity: 1; transform: translate(4px, 1px) }}
      9%  {{ opacity: 0; transform: none }}
      55% {{ opacity: 1; transform: translate(5px, 0) }}
      58% {{ opacity: 0; transform: none }}
    }}
    /* slices are only visible while they are displaced, so the calm frames stay clean */
    @keyframes sliceA {{
      0% {{ opacity: 1; transform: translateX(-28px) }} 2% {{ opacity: 1; transform: translateX(18px) }}
      5% {{ opacity: 1; transform: translateX(-10px) }} 8% {{ opacity: 0; transform: none }}
      55% {{ opacity: 1; transform: translateX(14px) }} 57% {{ opacity: 0; transform: none }}
    }}
    @keyframes sliceB {{
      0% {{ opacity: 1; transform: translateX(22px) }} 3% {{ opacity: 1; transform: translateX(-30px) }}
      6% {{ opacity: 1; transform: translateX(12px) }} 8% {{ opacity: 0; transform: none }}
    }}
    @keyframes sliceC {{
      0% {{ opacity: 0 }} 1% {{ opacity: 1; transform: translateX(-16px) }}
      4% {{ opacity: 1; transform: translateX(26px) }} 7% {{ opacity: 0; transform: none }}
      56% {{ opacity: 1; transform: translateX(-12px) }} 58% {{ opacity: 0; transform: none }}
    }}
    @keyframes bar {{
      0% {{ opacity: .9 }} 2% {{ opacity: 0 }} 4% {{ opacity: .7 }} 7% {{ opacity: 0 }}
    }}
    @keyframes spin  {{ to {{ transform: rotate(360deg) }} }}
    @keyframes scan  {{ from {{ transform: translateY(0) }} to {{ transform: translateY(8px) }} }}
    @keyframes pulse {{ 0%, 100% {{ opacity: .55 }} 50% {{ opacity: 1 }} }}
  </style>

  <defs>
    <clipPath id="circle"><circle cx="{C}" cy="{C}" r="{R}"/></clipPath>
    <g id="av" clip-path="url(#circle)">
      <image href="{href}" x="{x0}" y="{x0}" width="{2 * R}" height="{2 * R}" preserveAspectRatio="xMidYMid slice"/>
    </g>
    <filter id="redOnly" color-interpolation-filters="sRGB">
      <feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/>
    </filter>
    <filter id="cyanOnly" color-interpolation-filters="sRGB">
      <feColorMatrix type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/>
    </filter>
    <filter id="blur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6"/></filter>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{CYAN}"/>
      <stop offset=".5" stop-color="{PURPLE}"/>
      <stop offset="1" stop-color="{PINK}"/>
    </linearGradient>
    <pattern id="lines" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1.4" fill="#000"/>
    </pattern>
{slice_clips}
  </defs>

  <!-- neon halo + HUD rings -->
  <circle class="glow" cx="{C}" cy="{C}" r="{R + 4}" fill="none" stroke="url(#neon)" stroke-width="10" filter="url(#blur)"/>
  <circle cx="{C}" cy="{C}" r="{R + 4}" fill="none" stroke="url(#neon)" stroke-width="3"/>
  <circle class="ring1" cx="{C}" cy="{C}" r="{R + 18}" fill="none" stroke="{CYAN}" stroke-width="2.5"
          stroke-dasharray="60 14 8 14 120 30" opacity=".85"/>
  <circle class="ring2" cx="{C}" cy="{C}" r="{R + 28}" fill="none" stroke="{PINK}" stroke-width="1.5"
          stroke-dasharray="2 7" opacity=".8"/>

  <!-- black disc so the screen-blended channels add up to the real colours -->
  <circle cx="{C}" cy="{C}" r="{R}" fill="#000"/>

  <!-- the picture: normal copy + red and cyan channel copies for the RGB split -->
  <use class="base" href="#av"/>
  <use class="red"  href="#av" filter="url(#redOnly)"/>
  <use class="cyan" href="#av" filter="url(#cyanOnly)"/>

  <!-- displaced slices -->
{slice_layers}

  <!-- scanlines -->
  <g clip-path="url(#circle)" opacity=".22">
    <rect class="scan" x="{x0}" y="{x0 - 8}" width="{2 * R}" height="{2 * R + 16}" fill="url(#lines)"/>
  </g>

  <!-- neon tear lines that flash during the burst -->
{bars}

  {brackets}
</svg>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="JiroRaiden")
    ap.add_argument("--image", help="local image instead of downloading the GitHub avatar")
    ap.add_argument("--out", default="dist/glitch-avatar.svg")
    a = ap.parse_args()

    import os
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build_svg(load_image(a.user, a.image)))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
