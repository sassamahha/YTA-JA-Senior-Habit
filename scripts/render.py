#!/usr/bin/env python3
"""Minimal renderer for YTA JA senior habit slides."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as fh:

def parse_markdown(md_path: Path) -> tuple[dict, str, list[str]]:
    content = md_path.read_text(encoding="utf-8")
    parts = content.split("---")
    if len(parts) < 3:
        raise ValueError("Markdown missing frontmatter")
        
    body = "---".join(parts[2:]).strip()

    title = ""
    bullets: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("- "):
            bullets.append(line[2:].strip())
    if not title:
        raise ValueError("Title (H1) missing in markdown body")
    if not bullets:
        raise ValueError("No bullet points found in markdown body")
    return frontmatter, title, bullets


def load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    if not path:
        return ImageFont.load_default()
    font_path = Path(path)
    try:
        return ImageFont.truetype(str(font_path), size=size)
    except Exception:
        return ImageFont.load_default()


def wrap_lines(text: str, max_chars: int, max_lines: int = 2) -> list[str]:
    raw_lines = textwrap.wrap(text, width=max_chars) or [text]
    if len(raw_lines) <= max_lines:
        return raw_lines
    trimmed = raw_lines[:max_lines]
    ellipsis = "…"
    trimmed[-1] = trimmed[-1][: max(0, max_chars - 1)] + ellipsis
    return trimmed


def create_slide(title: str, bullet: str, cfg: dict) -> Image.Image:
    size_cfg = cfg.get("size", {})
    width = int(size_cfg.get("width", 1080))
    height = int(size_cfg.get("height", 1920))
    safe_padding = int(cfg.get("layout", {}).get("safe_padding_px", 72))
    max_chars = int(cfg.get("layout", {}).get("max_chars_per_line", 22))
    line_spacing = float(cfg.get("layout", {}).get("line_spacing", 1.15))

    bg_image_path = cfg.get("background", {}).get("image")
    background = None
    if bg_image_path:
        bg_path = Path(bg_image_path)
        if bg_path.exists():
            background = Image.open(bg_path).convert("RGB").resize((width, height))
    if background is None:
        background = Image.new("RGB", (width, height), color="white")

    draw = ImageDraw.Draw(background)

    title_font = load_font(cfg.get("fonts", {}).get("title"), size=72)
    body_font = load_font(cfg.get("fonts", {}).get("body"), size=56)

    colors = cfg.get("colors", {})
    title_color = colors.get("fg_title", "#111111")
    body_color = colors.get("fg_body", "#111111")

    # Draw title
    title_lines = wrap_lines(title, max_chars, max_lines=2)
    y = safe_padding
    for line in title_lines:
        draw.text((safe_padding, y), line, font=title_font, fill=title_color)
        y += int(title_font.size * line_spacing)

    # Draw bullet text
    bullet_lines = wrap_lines(bullet, max_chars, max_lines=2)
    y += int(title_font.size * 0.75)
    for line in bullet_lines:
        draw.text((safe_padding, y), line, font=body_font, fill=body_color)
        y += int(body_font.size * line_spacing)

    return background


def build_video(md_path: Path) -> Path:
    cfg = load_config(Path("config/style.yaml"))
    frontmatter, title, bullets = parse_markdown(md_path)
    duration = float(cfg.get("layout", {}).get("slide_sec", 7))
    clips: list[ImageClip] = []
    for bullet in bullets:
        slide_img = create_slide(title, bullet, cfg)
        clip = ImageClip(np.array(slide_img)).set_duration(duration)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    bgm_path = frontmatter.get("bgm")
    if bgm_path:
        audio_file = Path(bgm_path)
        if audio_file.exists():
            try:
                bgm_clip = AudioFileClip(str(audio_file)).volumex(0.25)
                bgm_clip = bgm_clip.set_duration(video.duration)
                video = video.set_audio(CompositeAudioClip([bgm_clip]))
            except Exception:
                pass

    output_path = md_path.with_suffix(".mp4")
    video.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        verbose=False,
        logger=None,
    )
    return output_path


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: render.py <markdown>", file=sys.stderr)
        sys.exit(1)
    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"File not found: {md_path}", file=sys.stderr)
        sys.exit(1)
    try:
        output = build_video(md_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {output}")


if __name__ == "__main__":
    main()
