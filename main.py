import feedparser
from datetime import datetime, timedelta, timezone
import sqlite3
import discord
from discord.ext import commands, tasks
import os

from config import TOKEN, CHANNEL_ID, UPDATE_INTERVAL, LAST_ARTICLE_RANGE, RSS_FEEDS

# Path inside container
DB_PATH = os.getenv("DATABASE_PATH", "data/articles.db")

# Ensure the folder exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

connection = sqlite3.connect(DB_PATH)
c = connection.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS articles (title TEXT, link TEXT)''')
connection.commit()

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


def record_article_in_db(article):
	c.execute("INSERT INTO articles (title, link) VALUES (?, ?)", (article.title, article.link))
	connection.commit()


def article_in_db(entry):
	c.execute("SELECT link FROM articles WHERE link=?", (entry.link,))
	if c.fetchone() is None:
		return False
	else:
		return True


def get_new_articles():
	new_articles = []

	for rss_feed in RSS_FEEDS:
		entries = feedparser.parse(rss_feed["url"]).entries
		for entry in entries:
			if not article_in_db(entry):
				pub_date = pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
				if datetime.now(timezone.utc) - pub_date <= timedelta(days=LAST_ARTICLE_RANGE):
					new_articles.append({"article": entry})

	return new_articles


def format_to_message(article):
	article_title = article["article"].title
	article_link = article["article"].link

	message = f"**{article_title}**"
	message += f"\n{article_link}"

	return message


@bot.event
async def on_ready():
	print(f'{bot.user} has connected to Discord!')
	post_new_articles.start()


@tasks.loop(minutes=UPDATE_INTERVAL)
async def post_new_articles():
	channel = bot.get_channel(CHANNEL_ID)

	new_articles = get_new_articles()
	for article in new_articles:
		message = format_to_message(article)
		await channel.send(message)
		record_article_in_db(article["article"])


if __name__ == "__main__":
	bot.run(TOKEN)
