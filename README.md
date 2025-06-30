# Discord Bot Generator

Gemini APIを使用してDiscordボットを自動生成するDiscordボットです。

## 機能

- `!make` コマンドでボットの説明を入力して新しいDiscordボットを生成
- インタラクティブモードで段階的にボットを作成
- 生成されたボットはzipファイルでダウンロード可能
- 必要なファイル（main.py、requirements.txt、.env.example）を自動生成

## Renderでのデプロイ方法

### 1. Renderアカウントの作成
[Render](https://render.com)でアカウントを作成してください。

### 2. 新しいWebサービスを作成
1. Renderダッシュボードで「New +」をクリック
2. 「Web Service」を選択
3. GitHubリポジトリを接続（このプロジェクトをGitHubにプッシュする必要があります）

### 3. 環境変数の設定
Renderダッシュボードで以下の環境変数を設定してください：

- `DISCORD_TOKEN`: Discordボットのトークン
- `GEMINI_API_KEY`: Google Gemini APIのキー

### 4. デプロイ設定
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`
- **Environment**: Python 3.11

### 5. デプロイ
「Create Web Service」をクリックしてデプロイを開始します。

## ローカルでの実行

1. 依存関係をインストール：
```bash
pip install -r requirements.txt
```

2. `.env`ファイルを作成：
```
DISCORD_TOKEN=your_discord_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

3. ボットを起動：
```bash
python main.py
```

## 使用方法

### 基本的な使用方法
```
!make 天気予報を教えてくれるボット
```

### インタラクティブモード
```
!make
```
その後、画面の指示に従ってボットを作成します。

## 必要なAPIキー

1. **Discord Bot Token**: [Discord Developer Portal](https://discord.com/developers/applications)で取得
2. **Gemini API Key**: [Google AI Studio](https://makersuite.google.com/app/apikey)で取得

## 注意事項

- このボットは24時間稼働する必要があります
- Renderの無料プランでは月間750時間の制限があります
- 本格的な運用には有料プランの使用を推奨します 