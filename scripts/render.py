#!/usr/bin/env python3
"""Minimal renderer for YTA JA senior habit slides."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import NoReturn


def _missing_dependency(module: str, details: str | None = None) -> NoReturn:
    """Print Japanese guidance when a dependency is missing."""
    base_message = (
        f"依存ライブラリ '{module}' が見つかりません。\n"
        "以下のコマンドを実行してから、再度このスクリプトを実行してください:\n"
        "  python -m pip install --upgrade pip\n"
        "  python -m pip install moviepy pillow numpy pyyaml\n"
    )
    if details:
        base_message += f"詳細: {details}\n"
    print(base_message, file=sys.stderr)
    sys.exit(2)


try:
    import numpy as np  # type: ignore
except ModuleNotFoundError as exc:
    _missing_dependency("numpy", str(exc))

try:
    from yaml import safe_load
except ModuleNotFoundError as exc:
    _missing_dependency("pyyaml", str(exc))

try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError as exc:
    _missing_dependency("pillow", str(exc))

try:
    from moviepy.editor import (
        AudioFileClip,
        CompositeAudioClip,
        ImageClip,
        concatenate_videoclips,
    )
except ModuleNotFoundError as exc:
    _missing_dependency("moviepy", str(exc))


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {config_path}"
        )
    with config_path.open("r", encoding="utf-8") as fh:
        return safe_load(fh) or {}


def parse_markdown(md_path: Path) -> tuple[dict, str, list[str]]:
    content = md_path.read_text(encoding="utf-8")
    parts = content.split("---")
    if len(parts) < 3:
        raise ValueError("frontmatter ブロック (---) が見つかりません")
    frontmatter = safe_load(parts[1]) or {}
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
        raise ValueError("本文に H1 見出し (# ) がありません")
    if not bullets:
        raise ValueError("箇条書き (- ) が 1 行も見つかりません")
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


def build_video(md_path: Path) -> tuple[Path, dict]:
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
    return output_path, {
        "title": title,
        "bullet_count": len(bullets),
        "slide_sec": duration,
        "total_duration": duration * len(bullets),
        "frontmatter": frontmatter,
    }


def print_summary(md_path: Path, info: dict, output: Path) -> None:
    title = info.get("title", "")
    bullet_count = info.get("bullet_count", 0)
    total_duration = info.get("total_duration", 0.0)
    frontmatter = info.get("frontmatter", {})
    hashtags = frontmatter.get("hashtags") or []
    hashtags_text = ", ".join(hashtags) if isinstance(hashtags, list) else str(hashtags)

    summary_lines = [
        "✅ レンダリングが完了しました。",
        f"  - 入力: {md_path}",
        f"  - 出力: {output}",
        f"  - タイトル: {title}",
        f"  - スライド数: {bullet_count}枚",
        f"  - 合計尺: {total_duration:.1f}秒",
    ]
    if hashtags_text:
        summary_lines.append(f"  - ハッシュタグ: {hashtags_text}")

    print("\n".join(summary_lines))


def main() -> None:
    if len(sys.argv) != 2:
        print("使い方: python scripts/render.py <マークダウンファイル>", file=sys.stderr)
        sys.exit(1)
    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"入力ファイルが見つかりません: {md_path}", file=sys.stderr)
        sys.exit(2)
    try:
        output, info = build_video(md_path)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(3)
    except ValueError as exc:
        print(f"マークダウンの形式に問題があります: {exc}", file=sys.stderr)
        sys.exit(4)
    except Exception as exc:
        print(f"予期しないエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(5)
    print_summary(md_path, info, output)


if __name__ == "__main__":
    main()
