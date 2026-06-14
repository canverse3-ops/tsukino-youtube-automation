from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "01_script" / "script.md"
OUTPUT_DIR = PROJECT_ROOT / "02_output"

CHANNEL_RULES = {
    "format": "ドラマ朗読形式",
    "protagonist": "40代日本人女性",
    "theme": "静かな違和感 × 正体暴き",
    "ending": "最後は問いで終わる",
    "prompt_policy": "シーンごとに画像生成プロンプトを作る",
}


@dataclass(frozen=True)
class Scene:
    scene_number: int
    title: str
    narration: str
    visual_direction: str
    channel_rules: dict[str, str]


CHARACTER_CONSISTENCY = (
    "same Japanese woman, 43 years old, shoulder length dark brown hair, "
    "soft facial features, natural makeup, slim face, consistent character design, "
    "same character as previous scenes"
)

IMAGE_STYLE = (
    "cinematic photo illustration, realistic illustration, Japanese drama, movie still, "
    "warm light, shallow depth of field, vertical 9:16 composition, emotional atmosphere, "
    "no text in image"
)

NEGATIVE_PROMPT = (
    "low quality, bad anatomy, extra fingers, deformed hands, text, logo, watermark, "
    "horror, overly bright, cartoonish"
)


@dataclass(frozen=True)
class Prompt:
    scene_number: int
    image_filename: str
    duration_seconds: int
    visual_summary_ja: str
    emotion_ja: str
    composition_ja: str
    camera_ja: str
    image_prompt_ja: str
    image_prompt_en: str
    negative_prompt: str
    character_consistency: str


def read_script(path: Path = INPUT_FILE) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"入力ファイルが見つかりません: {path}\n"
            "01_script/script.md を作成してから python src/main.py を実行してください。"
        )
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("01_script/script.md が空です。台本を入力してください。")
    return text


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
    return metadata, parts[2].strip()


def extract_title(metadata: dict[str, str], body: str) -> str:
    if metadata.get("title"):
        return metadata["title"]

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return "静かな違和感の正体"


def split_scenes(body: str) -> list[tuple[str, str]]:
    heading_pattern = re.compile(r"^(#{2,4})\s*(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(body))

    if matches:
        scenes: list[tuple[str, str]] = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
            title = match.group(2).strip()
            content = body[start:end].strip()
            if content:
                scenes.append((title, content))
        if scenes:
            return scenes

    horizontal_rule_pattern = re.compile(r"^\s*---\s*$", re.MULTILINE)
    slide_blocks = [block.strip() for block in horizontal_rule_pattern.split(body) if block.strip()]
    if len(slide_blocks) > 1:
        return [(f"Scene {index}", block) for index, block in enumerate(slide_blocks, start=1)]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    return [(f"Scene {index}", paragraph) for index, paragraph in enumerate(paragraphs, start=1)]


def build_visual_direction(narration: str) -> str:
    snippet = re.sub(r"\s+", " ", narration).strip()[:90]
    return (
        "40代日本人女性を主人公に、薄暗い日常空間で静かな違和感が漂う構図。"
        f"台本要素: {snippet}"
    )



def estimate_duration_seconds(narration: str) -> int:
    compact_text = re.sub(r"\s+", "", narration)
    return max(4, min(8, round(len(compact_text) / 12)))


def build_visual_summary(scene: Scene) -> str:
    snippet = re.sub(r"\s+", " ", scene.narration).strip()[:70]
    return f"{scene.title}。43歳の日本人女性が、日常の中で静かな違和感を抱く場面。台本要素: {snippet}"


def infer_emotion_ja(narration: str) -> str:
    if any(word in narration for word in ("気づ", "違和感", "なかった", "申し訳ない")):
        return "戸惑い、抑えた不安、内省"
    if any(word in narration for word in ("褒め", "喜ば", "必要")):
        return "寂しさ、承認への渇き、静かな切なさ"
    if any(word in narration for word in ("あなた", "？", "?")):
        return "問いかけ、余韻、静かな緊張"
    return "静かな緊張、孤独感、感情を抑えた表情"


def build_composition_ja(scene_number: int) -> str:
    if scene_number == 1:
        return "縦長9:16、主人公を画面中央やや下に配置、余白を広めに取り孤独感を出す"
    if scene_number % 2 == 0:
        return "縦長9:16、主人公を三分割構図の片側に配置、背景に生活感のある室内をぼかして入れる"
    return "縦長9:16、主人公の上半身を中心にした構図、暖かい光と影で心情を強調する"


def build_camera_ja(scene_number: int) -> str:
    if scene_number == 1:
        return "ミディアムショット、目線の高さ、浅い被写界深度"
    if scene_number % 2 == 0:
        return "クローズアップ、少し斜めから、背景を柔らかくぼかす"
    return "ミディアムクローズアップ、固定カメラ、映画のワンシーンのような自然な画角"

def normalize_question_ending(text: str) -> str:
    stripped = text.rstrip()
    if stripped.endswith(("?", "？")):
        return stripped
    return f"{stripped}\n\nあなたなら、この違和感の正体に気づけますか？"


def build_scenes(scene_blocks: Iterable[tuple[str, str]]) -> list[Scene]:
    scenes = []
    blocks = list(scene_blocks)
    for index, (title, narration) in enumerate(blocks, start=1):
        final_narration = normalize_question_ending(narration) if index == len(blocks) else narration
        scenes.append(
            Scene(
                scene_number=index,
                title=title,
                narration=final_narration,
                visual_direction=build_visual_direction(final_narration),
                channel_rules=CHANNEL_RULES,
            )
        )
    return scenes


def build_prompts(scenes: Iterable[Scene]) -> list[Prompt]:
    prompts = []
    for scene in scenes:
        visual_summary_ja = build_visual_summary(scene)
        emotion_ja = infer_emotion_ja(scene.narration)
        composition_ja = build_composition_ja(scene.scene_number)
        camera_ja = build_camera_ja(scene.scene_number)
        prompt_ja = (
            f"{visual_summary_ja}。感情: {emotion_ja}。構図: {composition_ja}。"
            f"カメラ: {camera_ja}。画像スタイル: {IMAGE_STYLE}。"
            f"キャラクター一貫性: {CHARACTER_CONSISTENCY}。"
            "画像内に文字を入れない。"
        )
        prompt_en = (
            "A 43-year-old Japanese woman in a quiet everyday scene, "
            "showing subtle unease and introspection, with foreshadowing for an emotional reveal. "
            f"Scene title: {scene.title}. "
            "Vertical 9:16 framing, cinematic medium close-up or close-up, warm dramatic light, "
            "soft background blur, natural facial expression, emotional Japanese drama mood. "
            f"Image style: {IMAGE_STYLE}. "
            f"Character consistency: {CHARACTER_CONSISTENCY}. No text in image."
        )
        prompts.append(
            Prompt(
                scene_number=scene.scene_number,
                image_filename=f"scene_{scene.scene_number:02}.png",
                duration_seconds=estimate_duration_seconds(scene.narration),
                visual_summary_ja=visual_summary_ja,
                emotion_ja=emotion_ja,
                composition_ja=composition_ja,
                camera_ja=camera_ja,
                image_prompt_ja=prompt_ja,
                image_prompt_en=prompt_en,
                negative_prompt=NEGATIVE_PROMPT,
                character_consistency=CHARACTER_CONSISTENCY,
            )
        )
    return prompts


def build_description(title: str, scenes: list[Scene]) -> str:
    first_scene = scenes[0].narration.replace("\n", " ")[:120]
    return (
        f"{title}\n\n"
        "40代日本人女性を主人公にした、静かな違和感から正体暴きへ進むドラマ朗読ショートです。\n"
        f"導入: {first_scene}\n\n"
        "#朗読 #ドラマ朗読 #YouTubeショート #月乃チャンネル"
    )


def write_outputs(title: str, scenes: list[Scene], output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    prompts = build_prompts(scenes)

    (output_dir / "scene.json").write_text(
        json.dumps([asdict(scene) for scene in scenes], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "prompts.json").write_text(
        json.dumps([asdict(prompt) for prompt in prompts], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "youtube_title.txt").write_text(f"{title}\n", encoding="utf-8")
    (output_dir / "youtube_description.txt").write_text(build_description(title, scenes), encoding="utf-8")
    (output_dir / "youtube_tags.txt").write_text(
        "月乃チャンネル,朗読,ドラマ朗読,YouTubeショート,40代女性,静かな違和感,正体暴き\n",
        encoding="utf-8",
    )
    (output_dir / "fixed_comment.txt").write_text(
        "あなたはどの場面で違和感に気づきましたか？コメントで教えてください。\n",
        encoding="utf-8",
    )


def main() -> None:
    raw_script = read_script()
    metadata, body = split_front_matter(raw_script)
    title = extract_title(metadata, body)
    scenes = build_scenes(split_scenes(body))
    write_outputs(title, scenes)
    print(f"Generated {len(scenes)} scenes in {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
