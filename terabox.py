from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import logging
import asyncio
from datetime import datetime
from pyrogram.enums import ChatMemberStatus
from dotenv import load_dotenv
from os import environ
import os
import time
from status import format_progress_bar
from video import download_video, upload_video
from web import keep_alive
from utils import verify_user, check_token, check_verification, get_token
from info import VERIFY, VERIFY_TUTORIAL, BOT_USERNAME

load_dotenv('config.env', override=True)

logging.basicConfig(level=logging.INFO)

api_id = os.environ.get('TELEGRAM_API', '')
if len(api_id) == 0:
    logging.error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)

api_hash = os.environ.get('TELEGRAM_HASH', '')
if len(api_hash) == 0:
    logging.error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)
    
bot_token = os.environ.get('BOT_TOKEN', '')
if len(bot_token) == 0:
    logging.error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)
dump_id = os.environ.get('DUMP_CHAT_ID', '')
if len(dump_id) == 0:
    logging.error("DUMP_CHAT_ID variable is missing! Exiting now")
    exit(1)
else:
    dump_id = int(dump_id)

fsub_id = os.environ.get('FSUB_ID', '')
if len(fsub_id) == 0:
    logging.error("FSUB_ID variable is missing! Exiting now")
    exit(1)
else:
    fsub_id = int(fsub_id)

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    user_mention = message.from_user.mention

    # Check if user is present
    if not await present_user(user_id):
        try:
            await add_user(user_id)
            logging.info(f"Added user {user_id} to the database")
        except Exception as e:
            logging.error(f"Failed to add user {user_id} to the database: {e}")

    # Check verification status
    verify_status = await db_verify_status(user_id)

    # Check verification expiration
    if verify_status["is_verified"] and VERIFY_EXPIRE < (time.time() - verify_status["verified_time"]):
        await db_update_verify_status(user_id, {**verify_status, 'is_verified': False})
        verify_status['is_verified'] = False
        logging.info(f"Verification expired for user {user_id}")

    text = message.text
    if "verify_" in text:
        _, token = text.split("_", 1)
        logging.info(f"Extracted token: {token}")
        if verify_status["verify_token"] != token:
            logging.warning(f"Invalid or expired token for user {user_id}")
            return await message.reply("Your token is invalid or expired. Try again by clicking /start.")
        await db_update_verify_status(user_id, {**verify_status, 'is_verified': True, 'verified_time': time.time()})
        logging.info(f"User {user_id} verified successfully")
        return await message.reply("Your token has been successfully verified and is valid for 12 hours.")

    if not verify_status["is_verified"]:
        btn = [[
            InlineKeyboardButton("Verify", url=await get_token(client, message.from_user.id, f"https://telegram.me/{BOT_USERNAME}?start="))
        ],[
            InlineKeyboardButton("How To Open Link & Verify", url=VERIFY_TUTORIAL)
        ]]
        await message.reply_text(
            text="<b>You are not verified !\nKindly verify to continue !</b>",
            protect_content=True,
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    if len(message.command) > 1:
        data = message.command[1]
        if data.split("-", 1)[0] == "verify":
            userid = data.split("-", 2)[1]
            token = data.split("-", 3)[2]
            if str(message.from_user.id) != str(userid):
                return await message.reply_text(
                    text="<b>Invalid link or Expired link !</b>",
                    protect_content=True
                )
            is_valid = await check_token(client, userid, token)
            if is_valid:
                await message.reply_text(
                    text=f"<b>Hey {message.from_user.mention}, You are successfully verified !\nNow you have unlimited access for all files till today midnight.</b>",
                    protect_content=True
                )
                await verify_user(client, userid, token)
            else:
                return await message.reply_text(
                    text="<b>Invalid link or Expired link !</b>",
                    protect_content=True
                )

    sticker_message = await message.reply_sticker("CAACAgUAAxkBAAJgv2Z6WDZMA7DVe4Xt2iwIkepCqL5XAALTCgACTEYQVr4X28SRTmMcNQQ")
    await asyncio.sleep(1.8)
    await sticker_message.delete()

    reply_message = (
        f"Welcome, {user_mention}.\n\n"
        "🌟 I am a terabox downloader bot. Send me any terabox link and I will download it within a few seconds and send it to you ✨."
    )
    join_button = InlineKeyboardButton("Join ❤️🚀", url="https://t.me/ultroid_official")
    developer_button = InlineKeyboardButton("Developer ⚡️", url="https://t.me/ultroidxTeam")
    reply_markup = InlineKeyboardMarkup([[join_button, developer_button]])
    await message.reply_text(reply_message, reply_markup=reply_markup)


async def is_user_member(client, user_id):
    try:     
        member = await client.get_chat_member(fsub_id, user_id)
        logging.info(f"User {user_id} membership status: {member.status}")
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking membership status for user {user_id}: {e}")
        return False

@app.on_message(filters.text)
async def handle_message(client, message: Message):
    user_id = message.from_user.id
    user_mention = message.from_user.mention
    is_member = await is_user_member(client, user_id)

    if not is_member:
        join_button = InlineKeyboardButton("ᴊᴏɪɴ ❤️🚀", url="https://t.me/jetmirror")
        reply_markup = InlineKeyboardMarkup([[join_button]])
        await message.reply_text("ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍᴇ.", reply_markup=reply_markup)
        return

    terabox_link = message.text.strip()
    if "terabox" not in terabox_link:
        await message.reply_text("ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴛᴇʀᴀʙᴏx ʟɪɴᴋ.")
        return

    reply_msg = await message.reply_text("sᴇɴᴅɪɴɢ ʏᴏᴜ ᴛʜᴇ ᴍᴇᴅɪᴀ...🤤")

    try:
        file_path, thumbnail_path, video_title = await download_video(terabox_link, reply_msg, user_mention, user_id)
        await upload_video(client, file_path, thumbnail_path, video_title, reply_msg, dump_id, user_mention, user_id, message)
    except Exception as e:
        logging.error(f"Error handling message: {e}")
        await reply_msg.edit_text("ғᴀɪʟᴇᴅ ᴛᴏ ᴘʀᴏᴄᴇss ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ.\nɪғ ʏᴏᴜʀ ғɪʟᴇ sɪᴢᴇ ɪs ᴍᴏʀᴇ ᴛʜᴀɴ 120ᴍʙ ɪᴛ ᴍɪɢʜᴛ ғᴀɪʟ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ.\nᴛʜɪs ɪs ᴛʜᴇ ᴛᴇʀᴀʙᴏx ɪssᴜᴇ, sᴏᴍᴇ ʟɪɴᴋs ᴀʀᴇ ʙʀᴏᴋᴇɴ, sᴏ ᴅᴏɴᴛ ᴄᴏɴᴛᴀᴄᴛ ʙᴏᴛ's ᴏᴡɴᴇʀ")

if __name__ == "__main__":
    keep_alive()
    app.run()
