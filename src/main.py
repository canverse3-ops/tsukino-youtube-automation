from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "01_script" / "script.md"
OUTPUT_DIR = PROJECT_ROOT / "02_output"
IMAGES_DIR = PROJECT_ROOT / "03_images"

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

CHARACTER_CONSISTENCY_JA = (
    "同じ日本人女性、43歳、肩までのダークブラウンの髪、柔らかい顔立ち、"
    "ナチュラルメイク、細めの輪郭、主人公固定、同一人物、consistent character design"
)

IMAGE_STYLE = (
    "YouTubeショート用縦長9:16、実写風イラスト、映画のワンシーン、"
    "Japanese drama style、movie still、warm ambient lighting、"
    "emotional storytelling、realistic illustration、high detail、no text in image"
)

IMAGE_STYLE_EN = (
    "vertical 9:16 for YouTube Shorts, photorealistic illustration, cinematic movie scene, "
    "Japanese drama style, movie still, warm ambient lighting, emotional storytelling, "
    "realistic illustration, high detail, no text in image"
)

NEGATIVE_PROMPT = (
    "low quality, text, logo, watermark, horror, scary face, distorted body, "
    "extra fingers, bad hands, old woman, elderly, cartoon, anime style, blurry, duplicate person"
)


@dataclass(frozen=True)
class SceneVisualDetails:
    location_ja: str
    time_ja: str
    expression_ja: str
    posture_ja: str
    props_ja: str
    lighting_ja: str
    composition_ja: str
    camera_ja: str
    emotion_ja: str
    location_en: str
    time_en: str
    expression_en: str
    posture_en: str
    props_en: str
    lighting_en: str
    composition_en: str
    camera_en: str
    emotion_en: str


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


@dataclass(frozen=True)
class ImageGenerationPlan:
    scene_number: int
    image_filename: str
    image_prompt_ja: str


@dataclass(frozen=True)
class ImagePrompt:
    scene_number: int
    image_filename: str
    duration_seconds: int
    narration: str
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


def compact_narration(narration: str, limit: int = 90) -> str:
    return re.sub(r"\s+", " ", narration).strip().rstrip("。.")[:limit]


def format_time_and_location(time_ja: str, location_ja: str) -> str:
    if location_ja.startswith(time_ja):
        return location_ja
    return f"{time_ja}の{location_ja}"


def build_visual_direction(narration: str) -> str:
    details = infer_scene_visual_details(1, narration)
    setting = format_time_and_location(details.time_ja, details.location_ja)
    return (
        f"{setting}で、{details.posture_ja}主人公。"
        f"表情は{details.expression_ja}、小物は{details.props_ja}。"
        f"台本要素: {compact_narration(narration)}"
    )


def estimate_duration_seconds(narration: str) -> int:
    compact_text = re.sub(r"\s+", "", narration)
    return max(4, min(8, round(len(compact_text) / 12)))


def infer_scene_visual_details(scene_number: int, narration: str) -> SceneVisualDetails:
    if any(word in narration for word in ("家で休み", "休みたかった")):
        return SceneVisualDetails(
            "夜の静かなリビング", "夜", "少し疲れて迷いを隠せない表情", "ソファに一人で浅く座り、片手にスマホを持って画面を見下ろす", "スマホ、薄いブランケット、ローテーブルの冷めたマグカップ、閉じかけの本", "暖かい間接照明、窓の外は暗い夜景、部屋の隅に柔らかい影", "縦長9:16、主人公を画面中央やや下、周囲に余白を残して孤独感を強調", "目線の高さのミディアムショット、浅い被写界深度、映画の静かな導入カット", "休みたい本音と断れない予感が混ざる内省",
            "a quiet living room at night", "night", "slightly tired, conflicted expression", "sitting alone on a sofa, holding a smartphone and looking down at the screen", "smartphone, light blanket, cold mug on a low table, half-closed book", "warm indirect lamp light, dark night outside the window, soft shadows in the room", "vertical 9:16, subject slightly low in the center with empty space emphasizing loneliness", "eye-level medium shot, shallow depth of field, quiet cinematic opening frame", "introspection between wanting to rest and sensing she cannot refuse",
        )
    if any(word in narration for word in ("いいよ", "返して")):
        return SceneVisualDetails("夜のリビングのソファ横", "夜", "小さく後悔しながら作り笑いを消した表情", "スマホを両手で持ち、送信直後の画面を見つめて肩を落とす", "スマホ、クッション、未整理のバッグ、テーブル上の鍵", "スマホ画面の冷たい光と暖色の室内灯が顔に混ざる", "縦長9:16、三分割構図で主人公を右側、左側に暗い余白", "斜め前からのクローズアップ、背景を柔らかくぼかす", "返事をした直後の自己犠牲と戸惑い", "beside the sofa in a living room", "night", "faint regret after a forced smile fades", "holding a smartphone with both hands, staring at the just-sent message, shoulders lowered", "smartphone, cushion, unorganized bag, keys on the table", "cool phone screen light mixed with warm room light on her face", "vertical 9:16, rule of thirds with her on the right and dark empty space on the left", "close-up from a slight front angle, softly blurred background", "confusion and self-sacrifice right after replying")
    if "行きたい" in narration:
        location="玄関前の廊下"; props="ハンドバッグ、玄関の靴、壁に掛かった薄手のコート"
        expr="自分の本音を押し込めるような硬い表情"; posture="外出前なのに足を止め、バッグの持ち手を握ったまま立ち尽くす"
    elif "優しい" in narration:
        location="洗面台の前"; props="鏡、洗面台の小さなタオル、ヘアブラシ"
        expr="優しさではないと気づいた静かな表情"; posture="鏡の前で視線を少しそらし、片手を洗面台につく"
    elif "申し訳ない" in narration:
        location="ダイニングテーブル"; props="スマホ、メモ帳、ペン、飲みかけのお茶"
        expr="罪悪感で眉を少し寄せた表情"; posture="椅子に座り、断る文章を書きかけたスマホを前に手を止める"
    elif "昔" in narration or "褒め" in narration:
        location="夕方のキッチン"; props="食器、ふきん、古い家族写真が入った小さなフォトフレーム"
        expr="過去を思い出す寂しげな表情"; posture="食器を拭く手を止め、棚の写真に視線を向ける"
    elif "我慢" in narration:
        location="ダイニングの椅子"; props="冷めた夕食、箸、折りたたまれたエプロン"
        expr="言葉を飲み込むような切ない表情"; posture="椅子に浅く座り、膝の上で両手を重ねてうつむく"
    elif "役に立つ" in narration or "必要" in narration:
        location="片付け途中のキッチン"; props="買い物袋、食材、メモ、エコバッグ"
        expr="必要とされる安心と寂しさが混ざった表情"; posture="買い物袋を持ったまま立ち止まり、少しだけ視線を落とす"
    elif "期待" in narration or "価値" in narration and "なって" in narration:
        location="夜の寝室のベッド脇"; props="手帳、ペン、ベッドサイドランプ、伏せたスマホ"
        expr="自分の価値を測ってしまうことに気づいた苦い表情"; posture="ベッド脇に座り、開いた手帳を見つめて背中を丸める"
    elif "断れない" in narration:
        location="薄明かりの玄関"; props="バッグ、靴、ドアチェーン、鍵"
        expr="理由を見抜き始めた凛とした表情"; posture="ドアの前で立ち止まり、鍵を握った手を胸元に寄せる"
    elif "断る自分" in narration:
        location="夜のリビングの窓際"; props="カーテン、スマホ、サイドテーブルのマグカップ"
        expr="自分を責めてしまう痛みをこらえる表情"; posture="窓際に立ち、片腕を抱えるようにして外を見つめる"
    else:
        location="夜明け前のリビング"; props="スマホ、冷めたマグカップ、薄いカーテン、ノート"
        expr="視聴者に問いかけるような静かでまっすぐな表情"; posture="窓辺の椅子に座り、スマホを伏せて顔を少し上げる"

    return SceneVisualDetails(location, "夕方から夜", expr, posture, props, "暖かい室内光と窓からの淡い外光、自然な影", "縦長9:16、主人公の上半身を中心、背景に生活感のある具体的な室内を入れる", "ミディアムクローズアップ、目線の高さ、浅い被写界深度", infer_emotion_ja(narration), location, "evening to night", expr, posture, props, "warm indoor light with faint window light and natural shadows", "vertical 9:16, upper body centered with concrete lived-in interior details", "eye-level medium close-up, shallow depth of field", infer_emotion_ja(narration))


def build_visual_summary(scene: Scene) -> str:
    details = infer_scene_visual_details(scene.scene_number, scene.narration)
    setting = format_time_and_location(details.time_ja, details.location_ja)
    return f"{setting}で、{details.posture_ja}場面。台本要素: {compact_narration(scene.narration, 70)}"


def infer_emotion_ja(narration: str) -> str:
    if any(word in narration for word in ("気づ", "違和感", "なかった", "申し訳ない")):
        return "戸惑い、抑えた不安、内省"
    if any(word in narration for word in ("褒め", "喜ば", "必要")):
        return "寂しさ、承認への渇き、静かな切なさ"
    if any(word in narration for word in ("あなた", "？", "?")):
        return "問いかけ、余韻、静かな緊張"
    return "静かな緊張、孤独感、感情を抑えた表情"


def build_composition_ja(scene_number: int, narration: str = "") -> str:
    return infer_scene_visual_details(scene_number, narration).composition_ja


def build_camera_ja(scene_number: int, narration: str = "") -> str:
    return infer_scene_visual_details(scene_number, narration).camera_ja


def build_prompt_ja(
    scene: Scene,
    visual_summary_ja: str,
    emotion_ja: str,
    composition_ja: str,
    camera_ja: str,
) -> str:
    details = infer_scene_visual_details(scene.scene_number, scene.narration)
    return (
        f"{CHARACTER_CONSISTENCY_JA}。"
        f"{IMAGE_STYLE}。"
        f"場所: {details.location_ja}。時間帯: {details.time_ja}。"
        f"主人公の表情: {details.expression_ja}。姿勢: {details.posture_ja}。"
        f"小物: {details.props_ja}。光: {details.lighting_ja}。"
        f"カメラ構図: {composition_ja}。カメラ: {camera_ja}。"
        f"感情: {emotion_ja}。"
        f"具体シーン: {visual_summary_ja}。"
        "文字、字幕、看板、ロゴ、透かしは入れない。スピリチュアル表現、ホラー表現、アニメ調を避ける。"
        f"台本の意味: {compact_narration(scene.narration, 120)}。"
    )


def build_prompt_en(scene: Scene) -> str:
    details = infer_scene_visual_details(scene.scene_number, scene.narration)
    return (
        f"{CHARACTER_CONSISTENCY}. "
        f"{IMAGE_STYLE_EN}. "
        f"Location: {details.location_en}. Time: {details.time_en}. "
        f"Expression: {details.expression_en}. Pose: {details.posture_en}. "
        f"Props: {details.props_en}. Lighting: {details.lighting_en}. "
        f"Composition: {details.composition_en}. Camera: {details.camera_en}. "
        f"Emotion: {details.emotion_en}. "
        "No text, no captions, no signs, no logos, no watermark, no spiritual imagery, no horror, no anime style. "
        f"Narrative meaning: {compact_narration(scene.narration, 120)}."
    )


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
        composition_ja = build_composition_ja(scene.scene_number, scene.narration)
        camera_ja = build_camera_ja(scene.scene_number, scene.narration)
        prompt_ja = build_prompt_ja(scene, visual_summary_ja, emotion_ja, composition_ja, camera_ja)
        prompt_en = build_prompt_en(scene)
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


def build_image_generation_plan(prompts: Iterable[Prompt]) -> list[ImageGenerationPlan]:
    return [
        ImageGenerationPlan(
            scene_number=prompt.scene_number,
            image_filename=prompt.image_filename,
            image_prompt_ja=prompt.image_prompt_ja,
        )
        for prompt in prompts
    ]


def build_image_prompts(scenes: Iterable[Scene]) -> list[ImagePrompt]:
    image_prompts = []
    for scene in scenes:
        visual_summary_ja = build_visual_summary(scene)
        image_prompts.append(
            ImagePrompt(
                scene_number=scene.scene_number,
                image_filename=f"scene_{scene.scene_number:02}.png",
                duration_seconds=estimate_duration_seconds(scene.narration),
                narration=scene.narration,
                image_prompt_ja=build_prompt_ja(
                    scene,
                    visual_summary_ja,
                    infer_emotion_ja(scene.narration),
                    build_composition_ja(scene.scene_number, scene.narration),
                    build_camera_ja(scene.scene_number, scene.narration),
                ),
                image_prompt_en=build_prompt_en(scene),
                negative_prompt=NEGATIVE_PROMPT,
                character_consistency=CHARACTER_CONSISTENCY,
            )
        )
    return image_prompts


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
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    (IMAGES_DIR / ".gitkeep").touch(exist_ok=True)

    prompts = build_prompts(scenes)
    image_generation_plan = build_image_generation_plan(prompts)
    image_prompts = build_image_prompts(scenes)

    (output_dir / "scene.json").write_text(
        json.dumps([asdict(scene) for scene in scenes], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "prompts.json").write_text(
        json.dumps([asdict(prompt) for prompt in prompts], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "image_prompts.json").write_text(
        json.dumps([asdict(prompt) for prompt in image_prompts], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "image_generation_plan.json").write_text(
        json.dumps([asdict(plan) for plan in image_generation_plan], ensure_ascii=False, indent=2),
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
