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

各シーンに対応する画像生成プロンプトを保存します。日本語プロンプト、英語プロンプト、ネガティブプロンプトを含みます。

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
