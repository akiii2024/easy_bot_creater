import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import zipfile
import asyncio
import google.generativeai as genai
import re

# .envファイルを最初に読み込む
load_dotenv()

# --- Gemini API ---
# .envファイルからAPIキーを読み込む
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEYが.envファイルに設定されていません。")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# インタラクティブモードの状態を管理する辞書
interactive_sessions = {}

def parse_gemini_response(response_text):
    """Gemini APIの応答からPythonコード、requirements、.env.exampleを抽出する"""
    # Pythonコードブロックを抽出
    python_code_match = re.search(r"```python\n(.*?)```", response_text, re.DOTALL)
    python_code = python_code_match.group(1).strip() if python_code_match else ""

    # requirements.txtのブロックを抽出
    requirements_match = re.search(r"```text\n(.*?)```", response_text, re.DOTALL)
    requirements = requirements_match.group(1).strip() if requirements_match else "py-cord\npython-dotenv" # デフォルト値

    # .env.exampleのブロックを抽出
    env_example_match = re.search(r"```env\n(.*?)```", response_text, re.DOTALL)
    env_example = env_example_match.group(1).strip() if env_example_match else "DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE" # デフォルト値

    # コマンド一覧を抽出
    commands_list = extract_commands_from_code(python_code)

    return python_code, requirements, env_example, commands_list

def extract_commands_from_code(python_code):
    """Pythonコードからコマンド一覧を抽出する"""
    commands = []
    
    # @bot.command()で定義されたコマンドを検索
    command_pattern = r'@bot\.command\([^)]*name\s*=\s*["\']([^"\']+)["\'][^)]*\)\s*\n\s*async def [^(]+\([^)]*\):\s*\n\s*"""(.*?)"""'
    matches = re.finditer(command_pattern, python_code, re.DOTALL)
    
    for match in matches:
        command_name = match.group(1)
        command_help = match.group(2).strip()
        commands.append(f"`!{command_name}` - {command_help}")
    
    # nameパラメータがない場合のパターン（関数名がコマンド名になる）
    func_pattern = r'@bot\.command\([^)]*\)\s*\n\s*async def ([^(]+)\([^)]*\):\s*\n\s*"""(.*?)"""'
    func_matches = re.finditer(func_pattern, python_code, re.DOTALL)
    
    for match in func_matches:
        command_name = match.group(1)
        command_help = match.group(2).strip()
        commands.append(f"`!{command_name}` - {command_help}")
    
    # 組み込みコマンドを追加
    commands.append("`!help` - 組み込みのヘルプコマンド")
    
    return commands

async def generate_bot_with_gemini(channel, author, bot_description):
    """Gemini APIを使用してDiscordボットのコードを生成する"""
    await channel.send(f"「{bot_description}」ですね。承知いたしました。Gemini APIに問い合わせて、ボットのコードを生成します...")

    prompt = f"""
あなたは優秀なDiscordボット開発アシスタントです。
以下のユーザーの要望に基づいて、`py-cord`ライブラリを使用したDiscordボットの完全なPythonソースコードと、そのボットの実行に必要なライブラリを記載した`requirements.txt`の内容、そして必要な環境変数を記載した`.env.example`の内容を生成してください。

**ユーザーの要望:**
{bot_description}

**出力形式のルール:**
1.  Pythonコードは、必ず`main.py`というファイル名で、単一のファイルにまとめてください。
2.  Pythonコードは、必ず Discord Bot Token を `.env` ファイルの `DISCORD_TOKEN` から読み込むようにしてください。
3.  生成するコードには、基本的なエラーハンドリングや、ボットがオンラインになったことを確認するための `on_ready` イベントを含めてください。
4.  **必ず`!commands`コマンドを実装してください。このコマンドは、ボットが持つ全てのコマンドの一覧と説明を表示するembedメッセージを送信するようにしてください。**
   - `!commands`コマンドは、ボットの全コマンドを一覧表示するembedを作成して送信してください
   - 各コマンドには説明文を付けてください
   - embedのタイトルは「📚 コマンド一覧」や「🤖 ボットヘルプ」など適切なものにしてください
   - 色は0x00ff00（緑色）を使用してください
5.  `requirements.txt` には、`py-cord` と `python-dotenv` を必ず含めてください。その他、コードでimportしているライブラリがあれば追記してください。
6.  `.env.example` には、ボットの実行に必要な環境変数を記載してください。最低限 `DISCORD_TOKEN` は必須です。その他、APIキーや設定値が必要な場合は適切に追加してください。
7.  最終的な出力は、以下の形式で、Pythonコード、`requirements.txt`の内容、`.env.example`の内容をそれぞれ指定の言語ブロックで囲んでください。他の説明文は一切含めないでください。

```python
# main.py の内容
(ここにPythonコードを記述)
```

```text
# requirements.txt の内容
(ここにrequirements.txtの内容を記述)
```

```env
# .env.example の内容
(ここに.env.exampleの内容を記述)
```
"""

    try:
        response = await model.generate_content_async(prompt)
        
        # APIからの応答を解析
        main_py_content, requirements_content, env_example_content, commands_list = parse_gemini_response(response.text)

        if not main_py_content:
            await channel.send("エラー: Gemini APIから有効なPythonコードを取得できませんでした。")
            return None, None, None, None

        return main_py_content, requirements_content, env_example_content, commands_list

    except Exception as e:
        await channel.send(f"Gemini APIとの通信中にエラーが発生しました: {e}")
        return None, None, None, None

async def start_interactive_session(ctx):
    """インタラクティブモードを開始する"""
    user_id = ctx.author.id
    
    # セッション情報を初期化
    interactive_sessions[user_id] = {
        'stage': 'bot_type',
        'bot_info': {},
        'channel': ctx.channel
    }
    
    embed = discord.Embed(
        title="🤖 Discord Bot 作成アシスタント",
        description="インタラクティブモードでボットを作成しましょう！\nまず、どのような種類のボットを作りたいか教えてください。",
        color=0x00ff00
    )
    embed.add_field(
        name="選択肢",
        value="1️⃣ **機能型ボット** - 特定の機能を持つボット（天気予報、翻訳、計算など）\n"
              "2️⃣ **管理型ボット** - サーバー管理用のボット（モデレーション、ロール管理など）\n"
              "3️⃣ **娯楽型ボット** - ゲームやエンターテイメント用のボット\n"
              "4️⃣ **その他** - 上記に当てはまらないボット",
        inline=False
    )
    embed.add_field(
        name="操作方法",
        value="数字（1-4）を入力するか、具体的な説明を書いてください。\n`cancel`と入力すると作成をキャンセルできます。\n`back`と入力すると前の項目に戻ります。",
        inline=False
    )
    
    await ctx.send(embed=embed)

async def handle_interactive_response(message):
    """インタラクティブモードでのユーザー応答を処理する"""
    user_id = message.author.id
    
    if user_id not in interactive_sessions:
        return False
    
    session = interactive_sessions[user_id]
    message_content = message.content.lower().strip()
    
    # キャンセル処理
    if message_content == 'cancel':
        del interactive_sessions[user_id]
        await message.channel.send("❌ ボット作成をキャンセルしました。")
        return True
    
    if message_content == 'back':
        current_stage = session['stage']
        
        # ステージの戻り順序を定義
        stage_order = ['bot_type', 'bot_name', 'bot_features', 'bot_commands', 'confirmation']
        
        try:
            current_index = stage_order.index(current_stage)
            if current_index > 0:
                # 前のステージに戻る
                previous_stage = stage_order[current_index - 1]
                session['stage'] = previous_stage
                
                # 各ステージのembedを生成する関数を呼び出し
                embed = await create_stage_embed(previous_stage, session)
                await message.channel.send(embed=embed)
            else:
                # 最初のステージの場合は戻れない
                await message.channel.send("⚠️ これ以上戻ることはできません。")
        except ValueError:
            await message.channel.send("⚠️ 無効なステージです。")
        
        return True
    
    # ステージに応じた処理
    if session['stage'] == 'bot_type':
        await handle_bot_type_stage(message, session, message_content)
    elif session['stage'] == 'bot_name':
        await handle_bot_name_stage(message, session, message_content)
    elif session['stage'] == 'bot_features':
        await handle_bot_features_stage(message, session, message_content)
    elif session['stage'] == 'bot_commands':
        await handle_bot_commands_stage(message, session, message_content)
    elif session['stage'] == 'confirmation':
        await handle_confirmation_stage(message, session, message_content)
    
    return True

async def handle_bot_type_stage(message, session, message_content):
    """ボットタイプの選択ステージ"""
    bot_type_map = {
        '1': '機能型ボット',
        '2': '管理型ボット', 
        '3': '娯楽型ボット',
        '4': 'その他のボット'
    }
    
    if message_content in bot_type_map:
        session['bot_info']['type'] = bot_type_map[message_content]
    else:
        # 自由記述の場合はそのまま使用
        session['bot_info']['type'] = message.content
    
    session['stage'] = 'bot_name'
    
    embed = discord.Embed(
        title="📝 ボットの名前を決めましょう",
        description=f"ボットタイプ: **{session['bot_info']['type']}**\n\nボットの名前を教えてください。",
        color=0x00ff00
    )
    embed.add_field(
        name="例",
        value="• WeatherBot\n• ModBot\n• GameBot\n• HelperBot",
        inline=False
    )
    
    await message.channel.send(embed=embed)

async def handle_bot_name_stage(message, session, message_content):
    """ボット名の入力ステージ"""
    session['bot_info']['name'] = message.content
    session['stage'] = 'bot_features'
    
    embed = discord.Embed(
        title="⚙️ ボットの機能を詳しく教えてください",
        description=f"ボット名: **{session['bot_info']['name']}**\n\nこのボットにどのような機能を持たせたいですか？",
        color=0x00ff00
    )
    embed.add_field(
        name="具体的に説明してください",
        value="例：\n• 天気予報を教えてくれる\n• サーバーのメンバーを管理する\n• 簡単なゲームを提供する\n• 翻訳機能がある",
        inline=False
    )
    
    await message.channel.send(embed=embed)

async def handle_bot_features_stage(message, session, message_content):
    """ボット機能の詳細ステージ"""
    session['bot_info']['features'] = message.content
    session['stage'] = 'bot_commands'
    
    embed = discord.Embed(
        title="🔧 コマンドについて",
        description="ボットにどのようなコマンドを持たせたいですか？",
        color=0x00ff00
    )
    embed.add_field(
        name="コマンドの例",
        value="• `!weather 東京` - 天気予報を表示\n• `!ban @user` - ユーザーをBAN\n• `!play` - ゲームを開始\n• `!help` - ヘルプを表示",
        inline=False
    )
    embed.add_field(
        name="自由記述",
        value="具体的なコマンドを書くか、「自動で決めて」と入力してください。",
        inline=False
    )
    
    await message.channel.send(embed=embed)

async def handle_bot_commands_stage(message, session, message_content):
    """コマンド設定ステージ"""
    if message_content == '自動で決めて':
        session['bot_info']['commands'] = '自動生成'
    else:
        session['bot_info']['commands'] = message.content
    
    session['stage'] = 'confirmation'
    
    # 確認画面を表示
    embed = discord.Embed(
        title="✅ ボットの設定を確認してください",
        color=0x00ff00
    )
    embed.add_field(name="ボットタイプ", value=session['bot_info']['type'], inline=True)
    embed.add_field(name="ボット名", value=session['bot_info']['name'], inline=True)
    embed.add_field(name="機能", value=session['bot_info']['features'], inline=False)
    embed.add_field(name="コマンド", value=session['bot_info']['commands'], inline=False)
    embed.add_field(
        name="確認",
        value="この設定でボットを作成しますか？\n`yes` - 作成開始\n`no` - 最初からやり直し\n`cancel` - キャンセル",
        inline=False
    )
    
    await message.channel.send(embed=embed)

async def handle_confirmation_stage(message, session, message_content):
    """確認ステージ"""
    if message_content == 'yes':
        # ボット作成を開始
        bot_description = f"""
ボットタイプ: {session['bot_info']['type']}
ボット名: {session['bot_info']['name']}
機能: {session['bot_info']['features']}
コマンド: {session['bot_info']['commands']}
"""
        
        await message.channel.send("🚀 ボットの作成を開始します...")
        
        # 既存のgenerate_bot_with_gemini関数を使用
        main_py, requirements_txt, env_example, commands_list = await generate_bot_with_gemini(message.channel, message.author, bot_description)
        
        if main_py and requirements_txt and env_example:
            # 一時ディレクトリを作成
            temp_dir = "new_bot_temp"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            # ファイルを生成
            main_py_path = os.path.join(temp_dir, "main.py")
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            env_example_path = os.path.join(temp_dir, ".env.example")

            with open(main_py_path, "w", encoding="utf-8") as f:
                f.write(main_py)
            with open(requirements_path, "w", encoding="utf-8") as f:
                f.write(requirements_txt)
            with open(env_example_path, "w", encoding="utf-8") as f:
                f.write(env_example)

            # zipファイルに圧縮
            bot_name_safe = session['bot_info']['name'].replace(' ', '_').replace('/', '_')
            zip_filename = f"{bot_name_safe}_bot.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                zipf.write(main_py_path, arcname="main.py")
                zipf.write(requirements_path, arcname="requirements.txt")
                zipf.write(env_example_path, arcname=".env.example")

            # zipファイルを送信
            await message.channel.send("✅ 新しいボットの準備ができました！", file=discord.File(zip_filename))

            # コマンド一覧を表示
            if commands_list:
                embed = discord.Embed(
                    title="📚 作成されたボットのコマンド一覧",
                    description="このボットで使用できるコマンドです：",
                    color=0x00ff00
                )
                
                # コマンド一覧をフィールドに追加
                commands_text = "\n".join(commands_list)
                if len(commands_text) > 1024:
                    # 長すぎる場合は分割
                    chunks = [commands_text[i:i+1024] for i in range(0, len(commands_text), 1024)]
                    for i, chunk in enumerate(chunks):
                        embed.add_field(
                            name=f"コマンド一覧 (その{i+1})" if len(chunks) > 1 else "コマンド一覧",
                            value=chunk,
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="コマンド一覧",
                        value=commands_text,
                        inline=False
                    )
                
                embed.add_field(
                    name="使用方法",
                    value="zipファイルをダウンロードしbot_launcherにドラッグ&ドロップしてください。\nbot_launcherのダウンロードはこちら\nhttps://github.com/akiii2024/DiscordBotLauncher/releases/download/v0.1.0-alpha/BotLauncher.exe",
                    inline=False
                )
                
                await message.channel.send(embed=embed)

            # 一時ファイルをクリーンアップ
            os.remove(zip_filename)
            os.remove(main_py_path)
            os.remove(requirements_path)
            os.remove(env_example_path)
            os.rmdir(temp_dir)
        
        # セッションを終了
        del interactive_sessions[message.author.id]
        
    elif message_content == 'no':
        # 最初からやり直し
        session['stage'] = 'bot_type'
        session['bot_info'] = {}
        
        embed = discord.Embed(
            title="🔄 最初からやり直しましょう",
            description="どのような種類のボットを作りたいか教えてください。",
            color=0x00ff00
        )
        embed.add_field(
            name="選択肢",
            value="1️⃣ **機能型ボット** - 特定の機能を持つボット（天気予報、翻訳、計算など）\n"
                  "2️⃣ **管理型ボット** - サーバー管理用のボット（モデレーション、ロール管理など）\n"
                  "3️⃣ **娯楽型ボット** - ゲームやエンターテイメント用のボット\n"
                  "4️⃣ **その他** - 上記に当てはまらないボット",
            inline=False
        )
        
        await message.channel.send(embed=embed)
        
    elif message_content == 'cancel':
        del interactive_sessions[message.author.id]
        await message.channel.send("❌ ボット作成をキャンセルしました。")

async def create_stage_embed(stage, session):
    """ステージに応じたembedを作成する"""
    embeds = {
        'bot_type': {
            'title': "🤖 Discord Bot 作成アシスタント",
            'description': "インタラクティブモードでボットを作成しましょう！\nまず、どのような種類のボットを作りたいか教えてください。",
            'fields': [
                {
                    'name': "選択肢",
                    'value': "1️⃣ **機能型ボット** - 特定の機能を持つボット（天気予報、翻訳、計算など）\n"
                            "2️⃣ **管理型ボット** - サーバー管理用のボット（モデレーション、ロール管理など）\n"
                            "3️⃣ **娯楽型ボット** - ゲームやエンターテイメント用のボット\n"
                            "4️⃣ **その他** - 上記に当てはまらないボット",
                    'inline': False
                },
                {
                    'name': "操作方法",
                    'value': "数字（1-4）を入力するか、具体的な説明を書いてください。\n`cancel`と入力すると作成をキャンセルできます。\n`back`と入力すると前の項目に戻ります。",
                    'inline': False
                }
            ]
        },
        'bot_name': {
            'title': "📝 ボットの名前を決めましょう",
            'description': f"ボットタイプ: **{session['bot_info'].get('type', '未設定')}**\n\nボットの名前を教えてください。",
            'fields': [
                {
                    'name': "例",
                    'value': "• WeatherBot\n• ModBot\n• GameBot\n• HelperBot",
                    'inline': False
                }
            ]
        },
        'bot_features': {
            'title': "⚙️ ボットの機能を設定しましょう",
            'description': f"ボット名: **{session['bot_info'].get('name', '未設定')}**\n\nボットにどのような機能を持たせたいですか？",
            'fields': [
                {
                    'name': "機能の例",
                    'value': "• メッセージへの自動返信\n• コマンドによる情報取得\n• ファイルの管理\n• ユーザーとのゲーム\n• その他の特別な機能",
                    'inline': False
                }
            ]
        },
        'bot_commands': {
            'title': "🔧 コマンドを設定しましょう",
            'description': f"機能: **{session['bot_info'].get('features', '未設定')}**\n\nボットで使用するコマンドや動作を具体的に教えてください。",
            'fields': [
                {
                    'name': "コマンドの例",
                    'value': "• `!hello` - 挨拶を返す\n• `!weather <地名>` - 天気予報を表示\n• `!kick @user` - ユーザーをキック",
                    'inline': False
                }
            ]
        }
    }
    
    if stage not in embeds:
        # デフォルトのembed
        embed = discord.Embed(
            title="❓ エラー",
            description="無効なステージです。",
            color=0xff0000
        )
        return embed
    
    stage_info = embeds[stage]
    embed = discord.Embed(
        title=stage_info['title'],
        description=stage_info['description'],
        color=0x00ff00
    )
    
    for field in stage_info['fields']:
        embed.add_field(
            name=field['name'],
            value=field['value'],
            inline=field['inline']
        )
    
    return embed

# --- Discord Bot ---
# load_dotenv()  # この行を削除（上で既に呼び出している）

# インテントを明示的に設定
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    # ボット自身のメッセージは無視
    if message.author == bot.user:
        return
    
    # インタラクティブモードの応答を処理
    if message.author.id in interactive_sessions:
        await handle_interactive_response(message)
        return
    
    # 通常のコマンド処理
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send("pong")

@bot.command(name="make")
async def make_bot(ctx, *, bot_description: str = None):
    """ユーザーの指示に基づき、Gemini APIを使って新しいDiscordボットを生成しzipで提供する"""
    
    # 引数がない場合はインタラクティブモードを開始
    if bot_description is None:
        await start_interactive_session(ctx)
        return
    
    main_py, requirements_txt, env_example, commands_list = await generate_bot_with_gemini(ctx.channel, ctx.author, bot_description)

    if main_py and requirements_txt and env_example:
        # 一時ディレクトリを作成
        temp_dir = "new_bot_temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # ファイルを生成
        main_py_path = os.path.join(temp_dir, "main.py")
        requirements_path = os.path.join(temp_dir, "requirements.txt")
        env_example_path = os.path.join(temp_dir, ".env.example")

        with open(main_py_path, "w", encoding="utf-8") as f:
            f.write(main_py)
        with open(requirements_path, "w", encoding="utf-8") as f:
            f.write(requirements_txt)
        with open(env_example_path, "w", encoding="utf-8") as f:
            f.write(env_example)

        # zipファイルに圧縮
        zip_filename = f"{bot_description.replace(' ', '_')}_bot.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            zipf.write(main_py_path, arcname="main.py")
            zipf.write(requirements_path, arcname="requirements.txt")
            zipf.write(env_example_path, arcname=".env.example")

        # zipファイルを送信
        await ctx.send("新しいボットの準備ができました！", file=discord.File(zip_filename))

        # コマンド一覧を表示
        if commands_list:
            embed = discord.Embed(
                title="📚 作成されたボットのコマンド一覧",
                description="このボットで使用できるコマンドです：",
                color=0x00ff00
            )
            
            # コマンド一覧をフィールドに追加
            commands_text = "\n".join(commands_list)
            if len(commands_text) > 1024:
                # 長すぎる場合は分割
                chunks = [commands_text[i:i+1024] for i in range(0, len(commands_text), 1024)]
                for i, chunk in enumerate(chunks):
                    embed.add_field(
                        name=f"コマンド一覧 (その{i+1})" if len(chunks) > 1 else "コマンド一覧",
                        value=chunk,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="コマンド一覧",
                    value=commands_text,
                    inline=False
                )
            
            embed.add_field(
                name="使用方法",
                value="1. ダウンロードしたzipファイルを解凍\n2. `.env.example`を`.env`にリネームしてトークンを設定\n3. `pip install -r requirements.txt`で依存関係をインストール\n4. `python main.py`でボットを起動",
                inline=False
            )
            
            await ctx.send(embed=embed)

        # 一時ファイルをクリーンアップ
        os.remove(zip_filename)
        os.remove(main_py_path)
        os.remove(requirements_path)
        os.remove(env_example_path)
        os.rmdir(temp_dir)

@make_bot.error
async def make_bot_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("`!make`コマンドの使い方が正しくありません。\n**例:** `!make 天気予報を教えてくれるボット`")
    else:
        await ctx.send(f"エラーが発生しました: {error}")


bot.run(os.getenv("DISCORD_TOKEN"))
