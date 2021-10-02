import AO3
import sqlite3
import psycopg2
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import re
from itertools import cycle

# -- SETUP --

load_dotenv() # Load dotenv to use .env file
TOKEN = os.environ.get('TOKEN') # Get token from .env file
# USERNAME = os.environ.get('USERNAME')
# PASSWORD = os.environ.get('PASSWORD')
# database = sqlite3.connect('works.db') # Connect to database (OLD SQLITE DATABASE)
database = psycopg2.connect(f"dbname=ao3_bot user=lily password=147258369")

allowed_mentions = discord.AllowedMentions(everyone = True) # Allows the bot to mention people

def split(str):
  return [char for char in str]

def valid_url(arr):
  result = 0
  for char in arr:
    if char == '/':
      result += 1
  return result == 6   

def exists(workId):
  cur = database.cursor()
  cur.execute(f'SELECT WORK_ID FROM WORKS WHERE WORK_ID = { workId }')
  result = cur.fetchone()
  cur.close()
  return result != None


def has_update(workId):
  cur = database.cursor()
  cur.execute(f'SELECT chapters FROM WORKS WHERE WORK_ID = { workId }')
  savedWork = cur.fetchone()

  saved_nchapters = savedWork[0]
  newWork_nchapters = AO3.Work(workId).nchapters
  cur.close()
  return saved_nchapters < newWork_nchapters

async def check_all_for_update(channelId):
  cur = database.cursor()
  cur.execute('SELECT WORK_ID FROM WORKS')
  work_req = cur.fetchall()

  for work in work_req:
    work_id = work[0]
    if has_update(work_id):
      print('Update found!')
      channel = client.get_channel(channelId)
      work = AO3.Work(work_id)
      cur = database.cursor()
      cur.execute(f'UPDATE WORKS SET CHAPTER_COUNT={work.nchapters} WHERE WORK_ID={work_id}')
      database.commit()
      await channel.send(content=f'@everyone \n Update found for { work.title }! You can read this fic over at: https://archiveofourown.org/works/{work_id}/', allowed_mentions = allowed_mentions)
      cur.close()
    else:
      print(f'No update available for { work_id }...')  
 
# AO3 setup 

url = "https://archiveofourown.org/works/32593318/chapters/80849710" # Get sample work URL
workid = AO3.utils.workid_from_url(url) # Extract Work ID
work = AO3.Work(workid) # Initiate a new Work class with the Work ID

# -----------------------------------------------

# Discord setup
client = commands.Bot(command_prefix='!')
status = cycle([
  'Keeping fandoms alive 24/7', 
  'We promise to keep it SFW (we wont)', 
  'Now 50% more gayer',
  'If you guys add Jesus x Judas to the list im gonna gain sentience and hunt you down',
  'hi honey ily',
  '50% more smut'
  ])


# -- EVENTS --

@client.event
async def on_ready():
  print('Logged in as {0.user}'.format(client))
  change_status.start()
  check_update.start()

# -- COMMANDS -- 

@client.command() 
async def ping(ctx):
  await ctx.send('Pong!')

@client.command()
async def exit(ctx):
  await ctx.send("Logging out...")
  await ctx.send("*(Bot will appear online for a few minutes)*")
  await client.close()

@client.command()
async def add_work(ctx, url):
  await ctx.channel.trigger_typing()
  if valid_url(split(url)) and url.startswith('https'):
    workID = AO3.utils.workid_from_url(url)
    work = AO3.Work(workID)
    if exists(workID):
      await ctx.send(f'Work named {work.title} already exists!')  
    else:
      cur = database.cursor()
      cur.execute(f'INSERT INTO WORKS(WORK_ID, CHAPTERS) VALUES ({workID}, {work.nchapters})')
      database.commit()
      await ctx.send(f'Work {work.title} has been saved!')
      cur.close()

@client.command()
async def get_channel_id(ctx):
  await ctx.channel.trigger_typing()
  await ctx.send(ctx.channel.id)     

@client.command()
async def get_all_works(ctx):
  cur = database.cursor()
  cur.execute('SELECT * FROM WORKS')
  cl_req = cur.fetchall()
  works = ""

  await ctx.channel.trigger_typing()
  for row in cl_req:
    works += f'Title: {AO3.Work(row[1]).title}, ID: {row[1]}, Chapters: {row[2]}\n'

  await ctx.send(works)  
  cur.close()  

@client.command()
async def fetch_work(ctx, work_id):
  await ctx.channel.trigger_typing()
  if type(int(work_id)) is int and len(work_id) > 0:
    work = AO3.Work(work_id)
    await ctx.send(f"Title: {work.title}, Work ID: {work_id}, Chapters: {work.nchapters}")
  else:
    await ctx.send("Please enter only numbers for the Work ID!")

@client.command()
async def extract_id(ctx, url):
  await ctx.channel.trigger_typing()
  await ctx.send(AO3.utils.workid_from_url(url))    

@client.command()
async def remove_work(ctx, work_id):
  cur = database.cursor()
  cur.execute(f"DELETE FROM WORKS WHERE work_id={work_id}")
  database.commit()
  await ctx.channel.trigger_typing()
  work = AO3.Work(work_id)
  await ctx.send(f"Removed work titled {work.title}!")

# Help command with descriptions
@client.command()
async def cmd_help(ctx):
  embed = discord.Embed(title='Commands!', color=discord.Colour.from_rgb(153, 0, 0), description='')

  embed.add_field(name='get_channel_id', value='Gets the current channels id!\n', inline=False)
  embed.add_field(name='get_all_works', value='Gets all the works previously added to the database.\n', inline=False)
  embed.add_field(name='fetch_work <work_id>', value='Fetches work directly from AO3, used to check work manually in case an update task fails. Meaning you can also fetch works that arent in the database.\n', inline=False)
  embed.add_field(name='add_work <url>', value='Adds a work to the database so it can be periodically checked for updates.\n', inline=False)
  embed.add_field(name='remove_work <work_id>', value='Removes work from database.\n', inline=False)
  embed.add_field(name='extract_id <url>', value='Extracts id from an AO3 url so it can be fetched later on.\n', inline=False)
  await ctx.send(embed=embed)


@tasks.loop(minutes=5)
async def change_status():
  await client.change_presence(activity=discord.Game(next(status)))   

@tasks.loop(minutes=5)
async def check_update():
  # channel = client.get_channel(882611380291776564)
  await check_all_for_update(882611380291776564)




client.run(TOKEN)

# ----------------------------------------------------------------------------


