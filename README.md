# Tsukino YouTube Automation

Obsidianで作成したYouTubeショート台本から、月乃チャンネル向けの制作ファイルを自動生成するPythonプロジェクトです。

## 目的

`01_script/script.md` を読み込み、以下のファイルを `02_output/` に生成します。

- `scene.json`
- `prompts.json`
- `youtube_title.txt`
- `youtube_description.txt`
- `youtube_tags.txt`
- `fixed_comment.txt`

現時点では、画像生成やYouTube投稿は実装していません。後からGemini API、Imagen API、YouTube APIを接続しやすいように、台本解析、シーン生成、プロンプト生成、出力処理を分けています。

## プロジェクト構成

```text
01_script/
  script.md
02_output/
src/
  main.py
README.md
```

## 実行方法

```bash
python src/main.py
```

## 入力ファイル

`01_script/script.md` にObsidianで作成した台本を保存してください。

タイトルは以下のどちらかから取得します。

1. YAML front matter の `title`
2. Markdownの最初の `# 見出し`

シーンは `##` から `####` の見出しごとに分割します。見出しがない場合は、空行で区切られた段落をシーンとして扱います。

### 入力例

```markdown
---
title: 隣の部屋から聞こえる声
---

## Scene 1
夜、主人公の美和は隣の部屋から聞こえる小さな声に気づいた。

## Scene 2
翌朝、管理人に確認すると、その部屋は三か月前から空室だと言われる。
```

## 月乃チャンネル専用ルール

生成時には以下のルールを反映します。

- ドラマ朗読形式
- 主人公は40代日本人女性
- 静かな違和感 × 正体暴き
- 最後は問いで終わる
- シーンごとに画像生成プロンプトを作る
- JSON形式で保存する

## 出力内容

### `scene.json`

各シーンの番号、タイトル、ナレーション、画像向けの視覚指示、月乃チャンネル専用ルールを保存します。

### `prompts.json`

各シーンに対応する画像生成API連携向けのプロンプト情報を保存します。安全な最小構成として、台本から決定できる値と共通設定を組み合わせて生成します。

| 項目 | 説明 |
| --- | --- |
| `scene_number` | 1から始まるシーン番号 |
| `image_filename` | 生成画像の保存ファイル名。例: `scene_01.png` |
| `duration_seconds` | ショート動画編集で使う想定表示秒数。台本量から4〜8秒の範囲で推定 |
| `visual_summary_ja` | シーン内容を日本語で要約した画像向け説明 |
| `emotion_ja` | 主人公の感情トーン |
| `composition_ja` | 縦長9:16画像の構図指定 |
| `camera_ja` | カメラ距離、角度、被写界深度などの指定 |
| `image_prompt_ja` | 日本語の画像生成プロンプト。シーン要約、感情、構図、カメラ、共通スタイル、共通キャラクター設定を含む |
| `image_prompt_en` | 英語の画像生成プロンプト。外部画像生成APIで使いやすいように共通スタイルとキャラクター設定を含む |
| `negative_prompt` | 低品質、崩れ、文字、ロゴ、透かしなどを避けるための共通ネガティブプロンプト |
| `character_consistency` | 全シーンで同一人物として描くための共通キャラクター設定 |

共通キャラクター設定は「43歳の日本人女性、肩までの濃い茶色の髪、柔らかい顔立ち、自然なメイク、細面、前後シーンと同一人物」として固定しています。画像スタイルは、写実的な映画風イラスト、日本のドラマ、暖かい光、浅い被写界深度、縦長9:16、画像内テキストなしを基本にしています。

### YouTube用テキスト

- `youtube_title.txt`: 動画タイトル
- `youtube_description.txt`: 動画説明文
- `youtube_tags.txt`: タグ
- `fixed_comment.txt`: 固定コメント

## 今後の拡張予定

`src/main.py` 内の処理は、将来的に以下のAPI連携用モジュールへ分割できます。

- Gemini API: 台本の整形、タイトル案、説明文生成
- Imagen API: `prompts.json` を使った画像生成
- YouTube API: タイトル、説明文、タグ、固定コメントを使った投稿自動化

APIキーや認証情報は、実装時に環境変数や `.env` で管理する想定です。秘密情報をリポジトリにコミットしないでください。

## GitHub Actionsでの自動生成

このリポジトリでは、`01_script/script.md` をPushしたときにGitHub Actionsで `python src/main.py` を自動実行し、`02_output/` 以下の制作ファイルを更新できます。

### 自動生成されるファイル

- `02_output/scene.json`
- `02_output/prompts.json`
- `02_output/youtube_title.txt`
- `02_output/youtube_description.txt`
- `02_output/youtube_tags.txt`
- `02_output/fixed_comment.txt`

### 運用手順

1. Cursorなどのエディタで `01_script/script.md` を編集して保存します。
2. GitHub Desktopなどで変更をコミットします。
3. `Push origin` でGitHubへPushします。
4. GitHub Actionsの `Generate outputs` ワークフローが自動実行されます。
5. `02_output/` に変更がある場合、GitHub Actionsが自動コミットして同じブランチへPushします。

### 無限ループ防止について

ワークフローはPush時に実行されますが、対象パスを `01_script/script.md` とワークフローファイルに限定しています。GitHub Actionsが `02_output/` だけを自動コミットした場合は再実行されないため、生成コミットによる無限ループを防ぎます。加えて、実行条件で `github-actions[bot]` によるPushを除外しています。
