import discord
from discord import app_commands
import requests
import json
import random
import os
from dotenv import load_dotenv

# .envファイルからトークンを読み込む
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 966704632246198376

# GASのデプロイURL（自身のGASのURLに変更）
GAS_API_URL = os.getenv("GAS_URL")

#アタッカーチームデータ
team_Attack = []

#ディフェンダーチーム
team_Defense = []

# GASからデータを取得する関数
def fetch_checked_rows():
    response = requests.get(GAS_API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Error: {response.status_code}"}

#取得したデータからカスタムチーム振り分け
def create_teams(participants, max_swaps=250):
    # 参加者リストをランダムに並べ替え
    random.shuffle(participants)
    
    # 最初に5人を選んでチームA、残りをチームBにする
    team_a = participants[:5]
    team_b = participants[5:10]
    
    # チームの実力が±5以内に収まるように調整
    sum_a = sum([p['rankPoint'] for p in team_a])
    sum_b = sum([p['rankPoint'] for p in team_b])
    
    swap_count = 0
    
    # チームAとチームBの合計値の差が±5以内に収まるまで再分け
    while abs(sum_a - sum_b) > 5 and swap_count < max_swaps:
        # チームAとチームBのメンバーをランダムに交換
        swap_index_a = random.choice(range(5))
        swap_index_b = random.choice(range(5, 10))
        
        # メンバーを交換
        team_a[swap_index_a], team_b[swap_index_b - 5] = team_b[swap_index_b - 5], team_a[swap_index_a]
        
        # 新しい合計を計算
        sum_a = sum([p['rankPoint'] for p in team_a])
        sum_b = sum([p['rankPoint'] for p in team_b])
        
        swap_count += 1  # 交換回数をカウント
        
    # 結果を表示
    if abs(sum_a - sum_b) <= 5:
        print("Teams successfully balanced after", swap_count, "swaps.")
    else:
        print("Teams not balanced after max swaps (", max_swaps, ").")
    
    print(f"team_A:{sum_a}")
    print(f"team_B:{sum_b}")
    
    return team_a, team_b
    
    

# Botクラスの作成
class MyBot(discord.Client):
    def __init__(self):
         # メンバー情報を取得するために、membersインテントを有効化
        intents = discord.Intents.default()
        intents.members = True  # メンバー関連のインテントを有効にする
        
        super().__init__(intents=intents)  # インテントを指定して親クラスを初期化
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        guild = discord.Object(id=GUILD_ID)
        try:
            await self.tree.sync(guild=guild)  # スラッシュコマンドを同期
            print("スラッシュコマンドがサーバーに同期されました")
        except Exception as e:
            print("コマンド同期時にエラーが発生しました: {e}")

bot = MyBot()

#/syncコマンド
@bot.tree.command(name="sync", description="スラッシュコマンドを手動で同期")
async def sync(interaction: discord.Interaction):
    await bot.tree.sync()
    await interaction.response.send_message("スラッシュコマンドを同期しました！", ephemeral=True)

# /custom コマンド
@bot.tree.command(name="custom", description="カスタムチーム分けを行います")
async def custom(interaction: discord.Interaction):
    global team_Attack, team_Defense

    await interaction.response.defer()
    data = fetch_checked_rows()
    print(data)
    result =create_teams(data)

    team_Attack, team_Defense = result

    message= "\nアタッカーチーム:\n"
    print("\nアタッカーチーム:")
    for p in team_Attack:
        message += f"{p['userName']}\n"
        print(f"Name: {p['userName']}, RankPoint: {p['rankPoint']}")
    
    message += "\nディフェンダーチーム:\n"
    print("\nディフェンダーチーム:")
    for p in team_Defense:
        message += f"{p['userName']}\n"
        print(f"Name: {p['userName']}, RankPoint: {p['rankPoint']}")

    await interaction.followup.send(message)

#startコマンド
@bot.tree.command(name="start", description="VCを移動させゲームを開始します")
async def start(interaction: discord.Interaction):
    global team_Attack, team_Defense

    await interaction.response.defer()
    # ここにVCチャンネルのIDを設定
    ATTACKER_VC_ID = 966704632917295179  # アタッカーチーム用VCのID
    DEFENDER_VC_ID = 1204099851915239496  # ディフェンダーチーム用VCのID

    # ギルド（サーバー）からVCを取得
    guild = interaction.guild
    attacker_vc = guild.get_channel(ATTACKER_VC_ID)
    defender_vc = guild.get_channel(DEFENDER_VC_ID)

    if not attacker_vc or not defender_vc:
        await interaction.followup.send("VCチャンネルが見つかりません。")
        return

    moved_members = []

    for player in team_Attack:
        try:
            # メンバー情報を取得
            member = await guild.fetch_member(player['userId'])# メンバーIDから取得
        except discord.errors.NotFound:
            # メンバーが見つからなかった場合、Noneを返す（または処理をスキップ）
            print(f"メンバー {player['userId']} は見つかりませんでした。")
            continue
        except Exception as e:
            # その他のエラー
            print(f"予期しないエラーが発生しました: {e}")
            continue 
        print(member)
        if member and member.voice:  # ユーザーがVCにいるかチェック
            await member.move_to(attacker_vc)  # VC移動
            moved_members.append(player['userName'])

    for player in team_Defense:
        try:
            # メンバー情報を取得
            member = await guild.fetch_member(player['userId'])# メンバーIDから取得
        except discord.errors.NotFound:
            # メンバーが見つからなかった場合、Noneを返す（または処理をスキップ）
            print(f"メンバー {player['userId']} は見つかりませんでした。")
            continue
        except Exception as e:
            # その他のエラー
            print(f"予期しないエラーが発生しました: {e}")
            continue 
        print(member)
        if member and member.voice:
            await member.move_to(defender_vc)
            moved_members.append(player['userName'])

    # 移動結果を送信
    if moved_members:
        await interaction.followup.send(f"以下のメンバーをVCへ移動しました:\n{', '.join(moved_members)}")
    else:
        await interaction.followup.send("移動対象のメンバーが見つかりませんでした。")

# Botを実行
bot.run(TOKEN)
