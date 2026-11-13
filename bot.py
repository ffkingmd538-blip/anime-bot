import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION ---
API_ID = 33048137
API_HASH = "94a4d1f437612096d1a5e5128e46b0d8"
BOT_TOKEN = "8935859436:AAFAVNkKAYU4PIC7u9W4ZKUfjiGDuhSpQEA"
MONGO_URI = "mongodb+srv://animebot:animebotopo@cluster0.xkwletj.mongodb.net/?retryWrites=true&w=majority"
DATABASE_NAME = "AnimeFileStore"

# Database Connection
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client[DATABASE_NAME]
files_col = db["anime_files"]

app = Client("AnimeBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- 1. CHANNEL POST PARSER ---
@app.on_message(filters.channel & (filters.document | filters.video))
async def parse_anime_caption(client: Client, message: Message):
    caption = message.caption or ""
    match = re.findall(r"#([\w\s_]+)", caption)
    
    if len(match) >= 3:
        anime_name = match[0].strip().replace("_", " ")
        season = match[1].strip()
        episode = match[2].strip()
        quality = match[3].strip() if len(match) > 3 else "HD"
        
        file_id = message.document.file_id if message.document else message.video.file_id
        
        await files_col.insert_one({
            "anime_name": anime_name,
            "season": season,
            "episode": episode,
            "quality": quality,
            "file_id": file_id
        })
        print(f"Saved: {anime_name} - {season} - {episode}")

# --- 2. START COMMAND & ANIME LIST ---
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    animes = await files_col.distinct("anime_name")
    
    if not animes:
        await message.reply("⚠️ বর্তমানে কোনো অ্যানিমে ফাইল ডেটাবেজে নেই!")
        return
        
    keyboard = []
    for anime in animes:
        keyboard.append([InlineKeyboardButton(anime, callback_data=f"anime_{anime}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply("🎬 **ASIAN ANIME ZONE - File Store**\n\nনিচ থেকে আপনার পছন্দের অ্যানিমে সিলেক্ট করুন:", reply_markup=reply_markup)

# --- 3. CALLBACK QUERY HANDLER ---
@app.on_callback_query()
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    
    if data.startswith("anime_"):
        anime_name = data.replace("anime_", "")
        seasons = await files_col.distinct("season", {"anime_name": anime_name})
        
        keyboard = []
        for season in seasons:
            keyboard.append([InlineKeyboardButton(season, callback_data=f"season_{anime_name}_{season}")])
        keyboard.append([InlineKeyboardButton("« Back to Home", callback_data="home")])
        
        await callback_query.message.edit_text(f"📁 **{anime_name}**\n\nএকটি সিজন সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("season_"):
        parts = data.split("_", 2)
        anime_name = parts[1]
        season = parts[2]
        
        episodes = await files_col.distinct("episode", {"anime_name": anime_name, "season": season})
        
        keyboard = []
        for ep in episodes:
            keyboard.append([InlineKeyboardButton(f"Episode {ep}", callback_data=f"ep_{anime_name}_{season}_{ep}")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data=f"anime_{anime_name}")])
        
        await callback_query.message.edit_text(f"📺 **{anime_name} - {season}**\n\nএকটি এপিসোড সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("ep_"):
        parts = data.split("_", 3)
        anime_name = parts[1]
        season = parts[2]
        ep = parts[3]
        
        files = await files_col.find({"anime_name": anime_name, "season": season, "episode": ep}).to_list(length=100)
        
        keyboard = []
        for f in files:
            keyboard.append([InlineKeyboardButton(f"📥 Download ({f['quality']})", callback_data=f"get_{f['_id']}")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data=f"season_{anime_name}_{season}")])
        
        await callback_query.message.edit_text(f"✨ **{anime_name} | {season} | Episode {ep}**\n\nকোয়ালিটি সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("get_"):
        from bson.ObjectId import ObjectId
        file_id_db = data.replace("get_", "")
        file_doc = await files_col.find_one({"_id": ObjectId(file_id_db)})
        
        if file_doc:
            await client.send_cached_media(
                chat_id=callback_query.from_user.id,
                file_id=file_doc["file_id"],
                caption=f"🎬 **{file_doc['anime_name']}**\n📌 **{file_doc['season']} - Ep {file_doc['episode']} ({file_doc['quality']})**\n✨ Powered by ASIAN ANIME ZONE"
            )
        await callback_query.answer("ফাইলটি আপনার ইনবক্সে পাঠিয়ে দেওয়া হয়েছে! 🚀", show_alert=True)

    elif data == "home":
        animes = await files_col.distinct("anime_name")
        keyboard = [[InlineKeyboardButton(anime, callback_data=f"anime_{anime}")] for anime in animes]
        await callback_query.message.edit_text("🎬 **ASIAN ANIME ZONE - File Store**\n\nনিচ থেকে আপনার পছন্দের অ্যানিমে সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

app.run()
  
