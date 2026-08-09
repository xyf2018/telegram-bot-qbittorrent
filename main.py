import logging
import math
from datetime import timedelta

import qbittorrentapi
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

proxy = 'http://127.0.0.1:7890'
PROXIES = {
    'http' : proxy,
    'https' : proxy,
}

qb = qbittorrentapi.Client(
    host='localhost',
    port=8080
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s%s" % (s, size_name[i])


async def magnet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        magnet_link = context.args[0]

        response = qb.torrents_add(urls=magnet_link)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    except IndexError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Provide magent link.")


async def torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file_name = update.message.document.file_name
        new_file = await update.message.effective_attachment.get_file()
        await new_file.download_to_drive(custom_path='temp/%s' % file_name)

        response = qb.torrents_add(torrent_files='temp/%s' % file_name)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    except:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Add torrent file failed.")


async def downloading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    downloading_tors = qb.torrents_info(status_filter='downloading', sort='name')
    result_html = ''
    for tor in downloading_tors:
        name = tor['name']
        progress = round(tor['progress'] * 100, 2)
        downloaded = convert_size(tor['downloaded'])
        amount_left = convert_size(tor['amount_left'])
        eta = tor['eta']
        result_html += f"""
        <tr>
            <td>{name}</td>
            <td>{progress}%</td>
            <td>{downloaded}</td>
            <td>{amount_left}</td>
            <td>{timedelta(seconds=eta)}</td>
        </tr>
        """
    html_str=f"""
    <table border="1">
    <thead>
    <tr>
        <th>Name</th>
        <th>Progress</th>
        <th>Downloaded</th>
        <th>Remaining</th>
        <th>ETA</th>
    </tr>
    </thead>
    <tbody>
        {result_html}
    </tbody>
    </table>
    """
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendRichMessage",
        json={
            "chat_id": update.effective_chat.id,
            "rich_message": {
                "html" : html_str,
                "skip_entity_detection" : True,
            },
        },
        proxies=PROXIES,
        timeout=30,
    )


async def completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    completed_tors = qb.torrents_info(status_filter='completed', sort='name')
    result_html = ''
    for tor in completed_tors:
        name = tor['name']
        total_size = convert_size(tor['total_size'])
        result_html += f"""
        <tr>
        <td>{name}</td>
        <td>{total_size}</td>
        </tr>
        """
    html_str=f"""
    <table border="1">
    <thead>
    <tr>
        <th>Name</th>
        <th>Size</th>
    </tr>
    </thead>
    <tbody>
        {result_html}
    </tbody>
    </table>
    """
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendRichMessage",
        json={
            "chat_id": update.effective_chat.id,
            "rich_message": {
                "html" : html_str,
                "skip_entity_detection" : True,
            },
        },
        proxies=PROXIES,
        timeout=30,
    )


if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).proxy(proxy).get_updates_proxy(proxy).get_updates_connection_pool_size(100).build()

    magnet_handler = CommandHandler('magnet', magnet, filters.User(USER_ID))
    torrent_handler = MessageHandler(filters.Document.FileExtension("torrent") & filters.User(USER_ID), torrent)
    downloading_handler = CommandHandler('downloading', downloading, filters.User(USER_ID))
    completed_handler = CommandHandler('completed', completed, filters.User(USER_ID))
    application.add_handler(magnet_handler)
    application.add_handler(torrent_handler)
    application.add_handler(downloading_handler)
    application.add_handler(completed_handler)

    application.run_polling()
