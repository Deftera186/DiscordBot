# bot.py
# coding=UTF-8

# importing BuiltIn libarys that we will need for some commands
import os
import random
import re
import time
from datetime import datetime
import asyncio
import string
import traceback
import json

# discord related libarys
import discord
from discord.ext import tasks
from discord.ext import commands
from discord.utils import get

# for loading token safe
from dotenv import load_dotenv

# To do some operations with apis
import requests
import aiohttp
from bs4 import BeautifulSoup

# We will not use most of the libary, 
# but we need some of the functions there to create a verified user
from FxP import *

# clearing previous output
os.system("clear")

# loading token and creating client instance
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = discord.Client()

# variables for the random messages that the bot can send
ohohohohohoohohsoiwanfpsafeaf = 0
random_flag = False

# flag to know what to send in case someone sends "תוכיח"
count_message_flag = False

STFU = False # Should the bot respond to messages?
IS_MC_SERVER_OPEN = False # checks if mc server is open or close
MC_EMBED = discord.Embed()

# setting up the prefix and removing the builtin help command(so we can replace it manually)
client = commands.Bot(command_prefix='בר ')
client.remove_command("help")




def generate_response(message):
    triggers = json.load(
        open(
            "triggers.json",
            "r",
            encoding="utf8"))["Triggers"]
    response = None
    for trigger in triggers:
        flag = False
        # one of the triggers is one of the message words
        if trigger["word_detection"]:
            if any(word == word_trigger for word in message.content.split()
                   for word_trigger in trigger["triggers"]):
                flag = True
        # one of the triggers is the exact message
        elif trigger["word_detection"] is None:
            if any(
                    message.content == word_trigger for word_trigger in trigger["triggers"]):
                flag = True
        # one of the triggers is in the message
        else:
            if any(
                    word_trigger in message.content for word_trigger in trigger["triggers"]):
                flag = True
        if flag:
            response = trigger["response"]
            if trigger["ping"]:
            	response = message.author.mention + " " + response
            break

    return response



@tasks.loop(seconds=300.0)
async def is_server_open():
    global IS_MC_SERVER_OPEN, MC_EMBED
    
    await client.wait_until_ready()

    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.mcsrvstat.us/2/77.139.89.110") as resp:
            data = json.loads(await resp.text())
            current_status = data["online"]
            if current_status:
                players = data["players"]["online"]
    print(f"\u001b[31m[{datetime.now()}] \u001b[34mChecking Mc server: server is open({current_status})\u001b[0m")

    embed = discord.Embed(
        title='סטטוס שרת המיינקראפט',
        description=f"השרת דלוק :)\nכרגע מחוברים בשרת {players} שחקנים!" if current_status else "השרת כבוי :(",
        colour=discord.Colour.green() if current_status else discord.Colour.red()
    )
    embed.set_footer(text="הבוט הרשמי על שם בר מורוותי")
    embed.set_author(name="סטטוס השרת", icon_url="https://cdn.discordapp.com/attachments/671803648971374634/672848970724147200/d348e8451b40d4dc.png")
    MC_EMBED = embed

    if (current_status) != IS_MC_SERVER_OPEN:
        print(f"\u001b[31m[{datetime.now()}] \u001b[34mChanging status!({IS_MC_SERVER_OPEN} -> {current_status})\u001b[0m")
        IS_MC_SERVER_OPEN = current_status
        channel = client.get_channel(750102239724699770)
        await channel.send(embed=MC_EMBED)
            

@tasks.loop(seconds=60.0)
async def pingcheck():
    ''' Checks the bot ping every minute and printing it to the screen.
    In addition, it is responsible for renaming the bot nickname(on all of the servers) to its current date.
    '''
    try:
    	# Since the actions done here depend on the bot being connected
    	# , we'll have to wait for it to connect.
        await client.wait_until_ready()
        await asyncio.sleep(1)

        # Collect date information
        dateTimeObj = datetime.now()
        D1 = int(str(dateTimeObj)[8:10])
        D2 = int(str(dateTimeObj)[5:7])
        D3 = int(str(dateTimeObj)[0:2])
        D4 = int(str(dateTimeObj)[11:13])

        # logging ping
        print(
            f"\u001b[31m[{dateTimeObj}] \u001b[34mping check: \u001b[33m{round(client.latency * 1000)}ms\u001b[0m")

        # Changes the nickname according to the date
        if D4 >= 0 and D4 <= 12:
            for server in client.guilds:
                try:
                    await server.me.edit(nick=f"{D1}.{D2}.{D3}")
                except Exception as e:
                    print(e)
        else:
            for server in client.guilds:
                try:
                	# In 6.9, just for the meme, we delete the dot from the name.
                    if (D1 == 6 and D2 == 9):
                        await server.me.edit(nick=f"69")
                    else:
                        await server.me.edit(nick=f"{D1}.{D2}")
                except Exception as e:
                    print(e)

    # This function is not perfect, 
    # so I need a lot of information to help me with DEBUG in case something fails.
    except Exception as e:
        print(e)



@client.event
async def on_ready():
    ''' When we loggged in to the user, 
    we will print it and change the status accordingly.
    '''
    dateTimeObj = datetime.now()
    print(
        f"\u001b[31m[{dateTimeObj}] \u001b[34mLogged in: \u001b[32m{client.user.name}\u001b[0m")
    await client.change_presence(activity=discord.Game(name='בר עזרה" = עזרה"'))


@client.event
async def on_message(message):
    global STFU
    if message.author == client.user or message.author.bot:
        return

    if message.guild is None:
        await message.channel.send("תן")

    if not STFU:
        if message.content == message.content:
            global ohohohohohoohohsoiwanfpsafeaf
            ohohohohohoohohsoiwanfpsafeaf += 1
            flying_pig = [message.content]
            flying_pig = flying_pig[0].split()
            global random_flag
            if not random_flag:
                global ran_num
                ran_num = random.randint(5, 30)
                random_flag = True

        dateTimeObj = datetime.now()
        print(f"\u001b[31m[{dateTimeObj}] \u001b[34mMessage recieved: \u001b[32m{message.content}\u001b[34m|Random message in \u001b[32m{ran_num - ohohohohohoohohsoiwanfpsafeaf} messages\u001b[0m")
        if random.uniform(0,100) <= 0.0001:
            role_id = 678341014695706670
            role = get(message.guild.roles, id=role_id)
            await message.author.add_roles(role)
            channel = client.get_channel(649710438346522645)
            await channel.send(f"קבלו את הנבחר <@{message.author.id}>")
        if ohohohohohoohohsoiwanfpsafeaf == ran_num:
            batol_met = [f"<@{message.author.id}> אתה בתול", f"<@{message.author.id}> יש לי קקי",
                         f"<@{message.author.id}> נכה", f"<@{message.author.id}> נכה בתול",
                         f"<@{message.author.id}> למה אתה מעליב אותי", f"<@{message.author.id}> אני אתן לך באן",
                         f"<@{message.author.id}> אני ארז ברז", f"<@{message.author.id}> אני אוהב אותך",
                         f"<@{message.author.id}> אני יודע לספור עד 10",
                         f"<@{message.author.id}> אני הבוט האגדי של בר האגדי",
                         f"<@{message.author.id}> אתה יודע לספור עד 10?", f"<@{message.author.id}> בוא נשיר את שיר התן",
                         f"<@{message.author.id}> עכשיו סתם תייגתי אותך כדי לעצבן אותך",
                         f"<@{message.author.id}> היי, אני חדשה פה", f"<@{message.author.id}> אתה גאון אני אוהב אותך",
                         f"<@{message.author.id}> אני חבר גאנג",
                         f"<@{message.author.id}> בונבנת לצמיתות. פנה לבתול ראשי למידע נוסף",
                         f"<@{message.author.id}> קוששה הוא קוששה", f"<@{message.author.id}> קוששה הוא לא קוששה",
                         f"<@{message.author.id}> זה כואב לי", f"<@{message.author.id}> אתה מכיר את בובספוג?",
                         f"<@{message.author.id}> מהי דעתך האובייקטיבית עליי?",
                         f"<@{message.author.id}> האם אתה שונא אותי?", f"<@{message.author.id}> בן כמה אתה?",
                         f"<@{message.author.id}> בן כמה אני?", f"<@{message.author.id}> אני יודע הכל עליך",
                         f"<@{message.author.id}> בוא אהובי, תן לי נשיקה, אני נכה",
                         f"<@{message.author.id}> <@!514499914646945793> הוא בריון",
                         f"<@{message.author.id}> מה היא דעתך על <@!514499914646945793> הבריון?",
                         f"<@{message.author.id}> אני מרגיש מקופח", f"<@{message.author.id}> למה אתם לא אוהבים אותי?",
                         f"<@{message.author.id}> אני בר מורוותי האמיתי",
                         "a"]
            response = random.choice(batol_met)
            if response == "a":
                try:
                    await message.author.create_dm()
                    await message.author.dm_channel.send(f'תן')
                except:
                    await message.author.dm_channel.send(f'תן')
            else:
                await message.channel.send(response)
                print(
                    f"\u001b[31m[{dateTimeObj}] \u001b[34mMessage sent: \u001b[32m{response}\u001b[0m")
                ohohohohohoohohsoiwanfpsafeaf = 0
                random_flag = False

        if (any(i in flying_pig for i in ['בר', 'בוט', '<@!654393263326756880>', '<@654393263326756880>']) and any(i in message.content for i in ['מטומטם', 'דביל', 'מעצבן', 'שונא אותך', 'מאעפן', 'מעאפן', 'חרא', 'זבל', 'טיפש', 'עוף מפה', 'זונה', 'מסריח', 'אפס', 'מזכיר את כלבלב חמוד', 'מנאייכ', 'שחיף', 'גובלין'])):
            muted_role = get(message.guild.roles, id=750684016344170507)
            user_roles = message.author.roles
            await message.author.edit(roles=[muted_role])
            await asyncio.sleep(180)
            await message.author.edit(roles=user_roles)
        
        response = generate_response(message)
        if response:
        	await message.channel.send(response)
        	dateTimeObj = datetime.now()
        	print(
                f"\u001b[31m[{dateTimeObj}] \u001b[34mMessage sent: \u001b[32m{response}\u001b[0m")

        if "טוב" in flying_pig and len(message.content) > 25:
            response = "קראתי את הכל, טעות קטנה, תוב*"
            await message.channel.send(response)
            dateTimeObj = datetime.now()
            print(
                f"\u001b[31m[{dateTimeObj}] \u001b[34mMessage sent: \u001b[32m{response}\u001b[0m")

        if "אתה יודע לספור" in message.content or "אני יודע לספור" in message.content:
            response = "גם אני יודע לספור עד 10"
            await message.channel.send(response)
            global count_message_flag
            count_message_flag = True
            dateTimeObj = datetime.now()
            print(
                f"\u001b[31m[{dateTimeObj}] \u001b[34mMessage sent: \u001b[32m{response}\u001b[0m")

        if message.content == "תוכיח":
            if count_message_flag:
                for num in range(1, 11):
                    await message.channel.send(num)
                    dateTimeObj = datetime.now()
                    print(
                        f"\u001b[31m[{dateTimeObj}] \u001b[34mMessage sent: \u001b[32m{num}\u001b[0m")
                count_message_flag = False
            else:
                response = "שתוק יזין"
                await message.channel.send(response)
                dateTimeObj = datetime.now()
                print(
                    f"\u001b[31m[{dateTimeObj}] \u001b[34mMessage sent: \u001b[32m{response}\u001b[0m")


        if "תסתום ל" == message.content[:7]:
            for role in message.author.roles:
                if role.id == 749221955080814613 or message.author.id == 403614338197487616 or role.id == 749314268633104395:
                    permitted = True
                    break
                else:
                    permitted = False
            if permitted:
                time_to_s = message.content[7:]
                if float(time_to_s) < 20 and float(time_to_s) > 0:
                    STFU = True
                    await message.channel.send("סותם ל" + str(float(time_to_s) * 60) + " שניות")
                    await asyncio.sleep(float(time_to_s) * 60)
                    STFU = False
                else:
                    await message.channel.send("לא ולא ולא אסתום!")
            else:
                await message.channel.send("מי אתה בכלל שיש לך את הזכות להגיד לי לסתום?!")

        if "בתול" == message.content:
            emojis = ['🇧', '🇦', '🇹', '🇺', '🇱']
            for emoji in emojis:
                await message.add_reaction(emoji)
            dateTimeObj = datetime.now()
            print(
                f"\u001b[31m[{dateTimeObj}] \u001b[34mEmojis added: \u001b[32m{emojis}\u001b[0m")
    await client.process_commands(message)


@client.event
async def on_member_join(member):
    ''' creates a new dm when a new member joins '''
    try:
        await member.create_dm()
        await member.dm_channel.send(f'שלום נכה. ברוך הבא לגאנג.')
    # If the user blocked the bot / did not allow messages to be sent,
    # we will just pass
    except discord.errors.Forbidden:
        pass

@client.command(aliases=["משתמש"])
@commands.cooldown(1, 300, commands.BucketType.user)
async def genereate(ctx, *username):
    ''' Creates a user in FxP and validates it 
    Note: For this command to work, the bot must be self-hosted
    '''
    chars = string.ascii_letters + string.digits + '+/'
    
    username = " ".join(username)
    email = await Emails.Generate_Email()
    password = ''.join(chars[c % len(chars)] for c in os.urandom(8))

    await ctx.send("יוצר משתמש עם שם המשתמש הבא: `" + username + '`')
    new_user = await FxP.add_member(username, password, email)
    if new_user:
        await ctx.send(f"משתמש נוצר, הנה קישור: https://www.fxp.co.il/member.php?u={new_user}\nהסיסמא למשתמש נשלחה בפרטי!")
        await ctx.message.author.send(f"שם משתמש: ||{username}||\nסיסמא: ||{password}||")
        if await Emails.verify_email(email):
            await ctx.send("משתמש אומת!")
    else:
        await ctx.send("פקודה זאת זמינה בארועים מיוחדים בלבד/על פי בקשות משתמשים\nפנה ל<@!403614338197487616> ובקש ממנו להדליק פקודה זאת")

@client.command(aliases=["תחזור"])
async def come_back(ctx):
	''' If the bot has been muted with an STFU command, 
	it can be returned with this command '''
	global STFU
	STFU = False
	await ctx.send("טוב")

@client.command(aliases=["תגיד"])
@commands.has_any_role(749221955080814613, 749613722791706685, 749310460951658656) # Admin, tech, dev
async def say(ctx, *words):
    ''' Deletes the original message and sends the message that the bot was told to say '''
    await ctx.message.delete()
    await ctx.send(" ".join(words))
    
    
@client.command(aliases=["מיינקראפט"])
async def minecraft(ctx):
    ''' Sends an embed that says whether the Minecraft server is open 
    based on the data that the bot gets every 15 seconds (does not check again).
    '''
    global MC_EMBED
    await ctx.send(embed=MC_EMBED)
        
@client.command(aliases=["תפרש", "מזה", "תגדיר"])
async def what_is(ctx, *phrase):
    ''' Uses a Milog site to interpret a phrase 

    TODO:
    1) Switch to aiohttp from requests.
    2) Clean code
    3) Add comments
    '''
    url = "https://milog.co.il/" + " ".join(phrase)
    r = requests.get(url)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'lxml')
    results = soup.find_all('div', class_="sr_e_txt")
    results_length = len(results)
    flag = True
    if results_length == 1:
        await ctx.send("לא מצאתי את מה שכתבת. האם התכוונת ל: " + results[0].text)
    else:
        message = results[0].text
        temp = results[0].find('a')
        if temp:
             if 'milog' in temp['href']:
                 flag = False
                 await what_is(ctx, re.search('https://milog.co.il/(.*?)/s/', temp['href']).group(1))
             else:
                 message += "\n" + temp['href'].replace(" ", "%20")
        if flag:
            await ctx.send(message)

@client.command(aliases=["עזרה"])
@commands.cooldown(1, 5, commands.BucketType.user)
async def help(ctx, *command):
    embed = discord.Embed(
        title='מי אני',
        description=""".אני בוט שנועד לשרת את חברי גאנג כספ, עיקר תפקידי הוא לתקשר איתכם בעזרת הודעות
.אני מבוסס על בר מורוותי, דמות באתר שנוהגת להספים למי שלא מכיר אותו
.בנוסף על כך, יש לי כמה פקודות יעילות, אציין אותם למטה
!אם תרצו לשפר בי משהו, תוכלו לעשות זאת בכך שתציעו הצעה במשוב ובדיחה""",
        colour=discord.Colour.gold()
    )
    embed.set_footer(text="הבוט הרשמי על שם בר מורוותי")
    embed.set_author(
        name="עזרה", icon_url="https://cdn.discordapp.com/attachments/671803648971374634/672848970724147200/d348e8451b40d4dc.png")
    if not len(command):
        command = ""
    else:
        command = command[0]
    if command in ["", "פקודות"]:
        embed.add_field(
            name="עזרה",
            value="""
            `בר עזרה <פקודות/ארועים>`
            במידה וריק שולח לכם את ההודעה הזאת. אחרת שולח לכם דף עזרה למה שביקשתם.""",
            inline=True
        )
        embed.add_field(
            name="בר תחזור",
            value="""אחד מהראשיים המרושעים השבית אותי? כל מה שאתם צריכים זה לקרוא לי. כתבו בר תחזור ואחזור.""",
            inline=True
        )
        embed.add_field(
            name="בר מיינקראפט",
            value="""
            `בר מיינקראפט`
                בר יודיע לכם את סטטוס השרת.""",
            inline=True
        )
        embed.add_field(
                name="בר תפרש <ביטוי>",
                value="""רוצים לדעת מה הפירוש של משהו? סתם משעמם לכם? בקשו מבר לפרש משהו!
        תומך גם במשפטים, מציע לכם מילים דומות, ואף מנסה להשלים לבד לפי מה שכתבתם.
        דוגמאות:
        בר תפרש בננה
        בר תפרש ראשון לציון
        בר תפרש יוניתלוי""",
                inline=True
        )
        embed.add_field(
            name="בר משתמש",
            value="""
            `בר משתמש <שם משתמש>`
                השם המשתמש יש לכתוב את שם המשתמש שלכם.
                הסיסמא תיוצר באופן רנדמולי ובטוח ותישלח אליכם לפרטי.
                בר יצור עבורכם אימייל, חשבון בכספ וגם יאמת את החשבון עם האימייל.
                שימו לב שהפקודה זמינה רק באירועים מיוחדים""",
            inline=True
        )
    if command in ["", "ארועים", "אירועים"]:
        embed.add_field(
            name="הודעות רנדומליות",
            value="""
            `.הודעה רנדומלית תישלח בממוצע כל 17.5 הודעות`
            .בנוסף לכל הפקודות והאפשרויות שיש לי, לעיתים אשלח הודעות רנדמוליות""",
            inline=True
        )

        embed.add_field(
            name="סטטוס שרת המיינקראפט",
            value="בר יודיע על סטטוס שרת המיינקראפט במידה והשתנה.",
            inline=False
        )
    await ctx.send(embed=embed)

@client.event
async def on_command_error(ctx, error):
    error = getattr(error, 'original', error)
    
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"בתול, עלייך לחכות `{int(error.retry_after)}` שניות לפני שתמשיך")

@client.event
async def on_error(event, *args):
    ''' If there was a problem with one of the messages, send details about the specific message. '''
    print(traceback.format_exc())

# Starts the threads and the bot.
pingcheck.start()
is_server_open.start()
client.run(TOKEN, bot=False)
input("bot is up!")
