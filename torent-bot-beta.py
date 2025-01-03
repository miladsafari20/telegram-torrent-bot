import asyncio
import os
import urllib.parse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import qbittorrentapi


QB_HOST = os.getenv('QB_HOST')
QB_PORT = os.getenv('QB_PORT')
QB_USERNAME = os.getenv('QB_USERNAME')
QB_PASSWORD = os.getenv('QB_PASSWORD')
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR')

# Connecting to qBittorrent
qb = qbittorrentapi.Client(host=f"{QB_HOST}:{QB_PORT}", username=QB_USERNAME, password=QB_PASSWORD)

try:
    qb.auth_log_in()
    print("Connected to qBittorrent.")
except qbittorrentapi.LoginFailed as e:
    print(f"Error connecting to qBittorrent: {e}")


# Start command
async def start(update: Update, context):
    await update.message.reply_text("سلام! لینک مگنت تورنت خود را ارسال کنید.")


# Function to reset qBittorrent connection
def reset_qbittorrent_connection():
    global qb
    qb = qbittorrentapi.Client(host=f"{QB_HOST}:{QB_PORT}", username=QB_USERNAME, password=QB_PASSWORD)
    try:
        qb.auth_log_in()
        print("Reconnected to qBittorrent.")
    except qbittorrentapi.LoginFailed as e:
        print(f"Error reconnecting to qBittorrent: {e}")


# Function to handle the download process
async def download_torrent(magnet_link, update, progress_message):
    try:
        # Add torrent for download
        torrent = qb.torrents_add(urls=magnet_link, save_path=DOWNLOAD_DIR)
        await update.message.reply_text("تورنت با موفقیت اضافه شد! وضعیت دانلود به‌زودی اعلام می‌شود.")

        downloading_torrents = {}

        while True:
            try:
                torrent_info = qb.torrents_info()

                for t in torrent_info:
                    if t.state == "downloading":
                        if t.hash not in downloading_torrents:
                            downloading_torrents[t.hash] = t.name

                        progress = t.progress * 100
                        progress_bar = "▮" * int(progress // 10) + "▯" * (10 - int(progress // 10))
                        download_speed = t.dlspeed
                        download_speed_kb = download_speed / 1024
                        download_speed_kbit = download_speed_kb * 8
                        download_speed_mbit = download_speed_kbit / 1024
                        downloaded_bytes = t.downloaded
                        total_size = t.size
                        downloaded_mb = downloaded_bytes / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        downloaded_gb = downloaded_mb / 1024
                        total_gb = total_mb / 1024
                        encoded_file_name = urllib.parse.quote(t.name)
                        dlink = f"http://oberstein.ayanokoji.ir/telegram_torent/{encoded_file_name}/"

                        await progress_message.edit_text(
                            f"⏳ وضعیت دانلود:\n[{progress_bar}] {progress:.2f}%\n\n"
                            f"📥 در حال دانلود: {t.name}\n\n"
                            f"🗂 حجم دانلود شده: {downloaded_mb:.2f} MB از {total_mb:.2f} MB\n\n"
                            f"یا {downloaded_gb:.2f} GB از {total_gb:.2f} GB\n\n"
                            f"🚀 سرعت دانلود: {download_speed_mbit:.2f} مگابیت بر ثانیه"
                        )

                    elif t.state == "pausedUP" or t.state == "completed":
                        if t.hash in downloading_torrents:
                            file_path = os.path.join(DOWNLOAD_DIR, t.name)
                            await progress_message.edit_text(
                                f"✅ دانلود کامل شد!\n\n"
                                f"🌐 لینک دانلود مستقیم:\n{dlink}\n\n"
                                f"💡 توجه: فایل برای مدت محدود در دسترس است."
                            )
                            del downloading_torrents[t.hash]
                            return  # Exit the function after download is complete

                await asyncio.sleep(2)
            except Exception as e:
                print(f"Error in download loop: {e}")
                reset_qbittorrent_connection()
                await asyncio.sleep(5)
                continue

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")


# Handling magnet link and starting the download
async def handle_magnet(update: Update, context):
    magnet_link = update.message.text.strip()

    if not magnet_link.startswith("magnet:?"):
        await update.message.reply_text("لطفاً یک لینک مگنت معتبر ارسال کنید.")
        return

    progress_message = await update.message.reply_text("در حال بررسی وضعیت دانلود...")

    # Run the download process in a separate task
    asyncio.create_task(download_torrent(magnet_link, update, progress_message))


# Build Telegram bot application
def main():
    # Telegram bot API key
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # Create the application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_magnet))

    # Start polling
    application.run_polling()


if __name__ == "__main__":
    main()
