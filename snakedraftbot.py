#ChatGPT 3.5 helped me write this. my python experience is throwing shit together until it works, so this helped expedite that process. i also received advice from a few friends, who can reach out if they'd like to be recognized

# IMPORT ALL THE THINGS
import discord
from discord.ext import commands
import os
import csv
from tabulate import tabulate
import random
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from typing import List, Literal
import json
import logging

# Set up the logger
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')


# create the member and draft_data dataclasses
@dataclass
class dMember:
    id: int
    name: str
    roster: List[dict]
    data: discord.Member

@dataclass
class DraftData:
    id: str
    name: str
    opt_in: bool
    members: List[dMember]
    draftees: List[dict]
    order: List[List[dMember]]
    turn: int
    status: Literal["initiated","started","cancelled","completed"]
    prevTurn: int
    lastDraft: datetime
    owner: dMember
    channel: int

# because i'm using discord.Member for member data, i need this to build json with it
def serialize_discord_member(member):
    return {
        'accent_color': int(member.accent_color) if member.accent_color else None,
        'accent_colour': int(member.accent_color) if member.accent_color else None,
        'activities': [str(activity) for activity in member.activities],
        'activity': str(member.activity) if member.activity else None,
        'avatar': str(member.avatar) if member.avatar else None,
        'banner': str(member.banner) if member.banner else None,
        'bot': member.bot,
        'color': int(member.color) if member.color else None,
        'colour': int(member.color) if member.color else None,
        'created_at': member.created_at.isoformat(),
        'default_avatar': str(member.default_avatar) if member.default_avatar else None,
        'desktop_status': str(member.desktop_status) if member.desktop_status else None,
        'discriminator': int(member.discriminator) if member.discriminator else None,
        'display_avatar': str(member.display_avatar) if member.display_avatar else None,
        'display_icon': str(member.display_icon) if member.display_icon else None,
        'display_name': member.display_name,
        'dm_channel': str(member.dm_channel) if member.dm_channel else None,
        'flags': int(member.flags) if member.flags else None,
        'global_name': str(member.global_name) if member.global_name else None,
        'guild': str(member.guild) if member.guild else None,
        'guild_avatar': str(member.guild_avatar) if member.guild_avatar else None,
        'guild_permissions': int(member.guild_permissions.value),
        'id': int(member.id) if member.id else None,
        'joined_at': member.joined_at.isoformat(),
        'mention': member.mention,
        'mobile_status': str(member.mobile_status) if member.mobile_status else None,
        'mutual_guilds': [str(guild) for guild in member.mutual_guilds],
        'name': member.name,
        'nick': member.nick,
        'pending': member.pending,
        'premium_since': member.premium_since.isoformat() if member.premium_since else None,
        'public_flags': str(member.public_flags) if member.public_flags else None,
        'raw_status': str(member.raw_status) if member.raw_status else None,
        'resolved_permissions': int(member.resolved_permissions.value) if member.resolved_permissions else None,
        'roles': [str(role) for role in member.roles],
        'status': str(member.status) if member.status else None,
        'system': member.system,
        'timed_out_until': member.timed_out_until.isoformat() if member.timed_out_until else None,
        'top_role': str(member.top_role) if member.top_role else None,
        'voice': str(member.voice) if member.voice else None,
        'web_status': str(member.web_status) if member.web_status else None
    }

# makes it so we can serialize the dataclasses w/ json
def custom_serializer(obj):
    if isinstance(obj, dMember):
        return obj.__dict__
    elif isinstance(obj, DraftData):
        obj_dict = obj.__dict__.copy()
        obj_dict['lastDraft'] = obj_dict['lastDraft'].isoformat() if obj_dict['lastDraft'] else None
        return obj_dict
    elif isinstance(obj, discord.Member):
        return serialize_discord_member(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

# only global variables, the list of all drafts and the record of notifications
draft_register = {}
notif_record = {}

# okay i lied, we can add a variable for how many backups we want to retain
max_backups = 7

# pull token from file
TOKEN = open("token.txt","r").readline()

# establish intents for bot
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.presences = True

# initialize bot
bot = commands.Bot(command_prefix='$',intents = intents,activity=discord.Activity(type=discord.ActivityType.watching, name='🐍 for $help'))

# test command
@bot.command()
async def testmsg(ctx):
    logging.info(f'test from {ctx.author.name} in {ctx.message.channel.id}')
    await ctx.send(f'{ctx.author.mention} test received :saluting_face:')

# input validation - is not negative
async def is_notNegative(ctx, val, valType, action, positive=False):
    user = ctx.author.name
    if positive:
        if val < 1:
            logging.info(f'{user} attempted to {action} with a non-positive value for {valType}')
            return None, None
        else:
            return user, val
    elif val < 0:
        logging.info(f'{user} attempted to {action} with a negative value for {valType}')
        return None, None
    else:
        return user, val

# input validation - draft name not already taken
async def validate_draftName(ctx, draft_name):
    user = ctx.author.name
    channel_id = ctx.message.channel.id
    channel_name = ctx.message.channel.name
    draft_id = f'{draft_name}-{channel_id}'
    if draft_id in draft_register:
        logging.info(f'{user} attempted to create a draft with name {draft_name}, in {channel_name} ({channel_id}) which is already created')
        return None, None
    return user, draft_name

# input validation - draft exists
async def is_draft(ctx, draft_name, action):
    user = ctx.author.name
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    if draft_id not in draft_register:
        logging.info(f'{user} attempted a {action} action for a draft that does not exist ({draft_id})')
        return None, None
    return user, draft_name

# input validation - is integer
async def is_integer(ctx, val, valType, action):
    user = str(ctx.author)
    if val is None:
        logging.info(f'{user} attempted to {action} without a value for {valType}')
        await ctx.send(f'please include a value for {valType} when attempting to {action}')
        return None, None
    try:
        val = int(val)
    except ValueError:
        logging.info(f'{user} attempted to {action} with an invalid value for {valType}')
        await ctx.message.channel.send(f'{valType} must be an integer')
        return None, None
    return user,val

# input validation - draft actions & ownership
async def validate_authorAction(ctx, draft, author, action, authorOnly=False, noStart=False):
    user = str(author.name)
    draft_id = f'{draft}-{ctx.message.channel.id}'
    draft = draft_register[draft_id]
    if draft.status == "cancelled":
        logging.info(f'{user} attempted to {action} an already-cancelled draft')
        await ctx.send(f'{draft.name} is already cancelled')
        return False
    elif draft.status == "completed":
        logging.info(f'{user} attempted to {action} an already-completed draft')
        await ctx.send(f'{draft.name} is already complete')
        return False
    elif noStart:
        if draft.status == "started":
            logging.info(f'{user} attempted to {action} an already-started draft')
            await ctx.send(f'{draft.name} is already started')
            return False
    elif authorOnly:
        if user == draft.owner:
            logging.info(f'{user} attempted to {action} a draft initiated by {draft.owner}')
            await ctx.send(f'draft {draft.name} belongs to {draft.owner}, and only the draft owner can {action}')
            return False
    else:
        return True

# check if there are enough draftees to execute the draft
async def can_execute(ctx, draft, num_rounds):
    draft_id = f'{draft}-{ctx.message.channel.id}'
    draft = draft_register[draft_id]
    return len(draft.draftees) >= len(draft.members) * num_rounds

# draft order
async def create_draftOrder(ctx, draft, num_rounds):
    draft_id = f'{draft}-{ctx.message.channel.id}'
    draft = draft_register[draft_id]
    rd_draft_order = list(draft.members)
#    if len(rd_draft_order) == 1:
#        draft.order.append(rd_draft_order)
#        i = 1
#        while i < num_rounds:
#            draft.order.append(rd_draft_order)
#            i += 1
#    else:
    random.shuffle(rd_draft_order)
    draft.order.append(rd_draft_order)
    i = 1
    while i < num_rounds:
        rd_draft_order = list(reversed(rd_draft_order))
        draft.order.append(rd_draft_order)
        i += 1
    return draft.order

# god python is a nightmare
async def get_member_by_id(draft, member_id):
    for member in draft.members:
        if int(member.id) == member_id:
            return member
    return None

# draft action
async def draft_draftee(ctx, draft, draftee_id):
    user = ctx.author.name
    draft_id = f'{draft}-{ctx.message.channel.id}'
    draft = draft_register[draft_id]
    drafter = await get_member_by_id(draft, ctx.author.id)
    if drafter:
        for i, draftee in enumerate(draft.draftees):
            if int(draftee['id']) == draftee_id:
                drafted = draft.draftees.pop(i)
                drafter.roster.append(drafted)
                logging.info(f'{user} drafted {drafted.name} in {draft.id}')
                await ctx.send(f'you drafted {drafted["name"]}')
                draft.turn += 1
                now = datetime.now()
                draft.lastDraft = now
                return True
            else:
                i += 1
    return None

# reminds the current drafter to draft
async def timeCheck():
    global draft_register, notif_record
    while True:
        for draft in draft_register.values():
            now = datetime.now()
            then = draft.lastDraft
            if (now - then) > timedelta(hours=24) and draft.status == "started":
                current_drafter = draft.order[draft.turn]
                current_drafter_draft = f'{current_drafter} - {draft.name}'
                if current_drafter_draft in notif_record:
                    last = notif_record[current_drafter_draft]
                    if (now - last) > timedelta(hours=24):
                        logging.info(f'notified {current_drafter.name} that they still need to pick')
                        reply_all(f'<@{current_drafter.id}>, it\'s still your turn to draft')
                        notif_record[current_drafter_draft] = now
                        return
                else:
                    logging.info(f'notified {current_drafter.name} that they still need to pick')
                    reply_all(f'<@{current_drafter.id}>, it\'s still your turn to draft')
                    notif_record[current_drafter_draft] = now
        await asyncio.sleep(6)

async def draftCompleteCheck():
    global draft_register
    while True:
        for draft in draft_register.values():
            if (draft.status == "started") and (draft.turn >= len(draft.order)):
                ctx = None
                await send_message(ctx, draft,f'a draft has completed')
                draft.status = "completed"
                await send_message(ctx, draft,f'Rosters:')
                await printRoster(ctx, draft.name)
                await send_message(ctx, draft,f'backing up the register')
                save_json()
        await asyncio.sleep(6)

async def turnCheck():
    global draft_register
    while True:
        for draft in draft_register.values():
            if (draft.status == "started") and (draft.turn > draft.prevTurn):
                ctx = None
                next_member = draft.order[draft.turn][0]
                await send_message(ctx, draft,f'it is now <@{next_member.id}>\'s turn')
                draft.prevTurn = draft.turn
        await asyncio.sleep(20)

async def printRoster(ctx, draft):
    draft_id = f'{draft}-{ctx.message.channel.id}'
    draft = draft_register[draft_id]
    if ctx == None:
        for member in draft.members:
            logging.info(f'printing roster for {member.name}')
            data = tabulate(member.roster, headers="keys", tablefmt="grid")
            await send_message(ctx, draft.name,f'<@{member.id}>:\n\n```{data}```')
    else:
        user = ctx.author.name
        logging.info(f'printing roster for {user}')
        drafter = await get_member_by_id(draft, ctx.author.id)
        data = tabulate(drafter.roster, headers="keys", tablefmt="grid")
        await ctx.send(draft.name,f'<@{drafter.id}>:\n\n```{data}```')

async def reply_all(message):
    for guild in bot.guilds:
        for channel in guild.text_channels:
            await channel.send(message)
            await asyncio.sleep(2)

async def send_message(ctx, draft, message):
    if ctx == None:
        draft_id = draft.id
    else:
        draft_id = f'{draft}-{ctx.message.channel.id}'
    draft = draft_register[draft_id]
    channel = bot.get_channel(draft.channel)
    if channel:
        await channel.send(message)
    else:
        logging.info(f'could not find the channel for {draft.name}')

# storing the draft register as json
def save_json():
    if os.path.exists('draft_register.json'):
        for i in range(max_backups-3, -1, -1):
            current_backup = f'draft_register.json.{i}'
            next_backup = f'draft_register.json.{i+1}'
            if os.path.exists(current_backup):
                os.rename(current_backup, next_backup)
        os.rename('draft_register.json','draft_register.json.0')
    with open('draft_register.json','w') as json_file:
        json.dump(draft_register, json_file, default=custom_serializer)

# retrieving the draft register as json
def load_json():
    global draft_register
    try:
        with open('draft_register.json','r') as json_file:
            draft_register = json.load(json_file)
    except FileNotFoundError:
        logging.info("no data found")

#
# bot commands
#


# $initiate (creates the draft)
@bot.command()
async def initiate(ctx, draft_name: str = commands.parameter(default=False, description="-- name of the new draft"), draft_type: str = commands.parameter(default="opt-out", description="-- optional, type 'opt-in' if you don't want your draft to automatically include everybody in the server")):
    """
    creates a new draft
    example:
		$initiate draft_name [opt-in]
    """
    global draft_register
    await validate_draftName(ctx, draft_name)
    user = str(ctx.author)
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    opt_in = draft_type == 'opt-in'
    if opt_in == True:
        logging.info(f'{user} has initiated an opt-in draft, {draft_id}')
        members = []
    else:
        logging.info(f'{user} has initiated a draft, {draft_name}')
        members = [dMember(
            id = str(member.id),
            name = member.name,
            roster = [],
            data = member
        ) for member in ctx.channel.members if not member.bot]
    await ctx.message.channel.send(f'draft {draft_name} initiated')
    await ctx.message.channel.send(f'please load a draftee list in csv format via $load {draft_name}')
    now = datetime.now()
    data = DraftData(
        id = f'{draft_name}-{ctx.message.channel.id}',
        name = draft_name,
        opt_in = opt_in,
        members = members,
        draftees = [],
        order = [],
        turn = 0,
        status = "initiated",
        prevTurn = 0,
        lastDraft = now,
        owner = user,
        channel = ctx.message.channel.id
    )
    draft_register[draft_id] = data
    return

@bot.command()
async def opt_in(ctx, draft_name: str = commands.parameter(default=None, description="-- name of the draft you're trying to opt into")):
    """
    opts the user into a draft
    example:
		$opt_in draft_name
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name,"opt-in")
    if user is None or draft_name is None:
        return
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    member_ids = {str(member.id) for member in draft_register[draft_id].members}
    if str(ctx.author.id) in member_ids:
        await ctx.send(f'you\'ve already opted in. if you want to opt back out, use $opt_out {draft_name}')
    else:
        new_member = dMember(
            id = str(ctx.author.id),
            name =  ctx.author.name,
            roster = [],
            data =  ctx.author
        )
        draft_register[draft_id].members.append(new_member)
        await ctx.send(f'you\'ve been opted in to {draft_name}')

@bot.command()
async def opt_out(ctx, draft_name: str = commands.parameter(default=None, description="-- name of the draft you're trying to opt out of")):
    """
    opts the user out of a draft
    example:
		$opt_out draft_name
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name,"opt-out")
    if user is None or draft_name is None:
        return
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    member_ids = {str(member.id) for member in draft_register[draft_id].members}
    if str(ctx.author.id) in member_ids:
        new_member = dMember(
            id = str(ctx.author.id),
            name =  ctx.author.name,
            roster = [],
            data =  ctx.author
        )
        draft_register[draft_id].members.remove(new_member)
        await ctx.send(f'you\'ve been opted out of {draft_name}')
    else:
        await ctx.send(f'you\'ve already opted out. if you want to opt back in, use $opt_in {draft_name}')

@bot.command()
async def cancel(ctx, draft_name: str = commands.parameter(default=None,description="-- name of the draft you're trying to cancel")):
    """
    cancels a draft
    only the owner of a draft can cancel
    example:
		$cancel draft_name
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name, "cancel")
    if user is None or draft_name is None:
        return
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    if validate_authorAction(ctx, draft_name, ctx.author, "cancel"):
        logging.info(f'{user} has cancelled draft {draft_name}')
        await ctx.send(f'draft {draft_name} has been cancelled')
        draft_register[draft_id].status = "cancelled"

@bot.command()
async def load(ctx, draft_name: str = commands.parameter(default=None,description="-- name of the draft you're trying to load draftees into"), test: bool = commands.parameter(default=False,description="-- used for testing, if you set this you're only causing problems")):
    """
    loads draftees into a draft
    only the owner of a draft can load
    attach the csv with draftees in it to the message with the command
    example:
		$load draft_name
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name, "load")
    if user is None or draft_name is None:
        return
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    if await validate_authorAction(ctx, draft_name, ctx.author, "load"):
        if test == True:
            with open(".\\sample\\sample.csv",'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    id = row['id']
                    name = row['name']
                    other_fields = {key: value for key, value in row.items() if key not in ['id', 'name']}
                    draft_register[draft_id].draftees.append({'id':id,'name':name,**other_fields})
            await ctx.send("loaded draftees successfully")
        elif ctx.message.attachments:
            if len(ctx.message.attachments) == 1:
                attachment = ctx.message.attachments[0]
                if attachment.filename.endswith('.csv'):
                    await attachment.save(attachment.filename)
                    with open(attachment.filename, 'r') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            id = row['id']
                            name = row['name']
                            other_fields = {key: value for key, value in row.items() if key not in ['id', 'name']}
                            draft_register[draft_id].draftees.append({'id':id,'name':name,**other_fields})
                    os.remove(attachment.filename)
                    await ctx.send("loaded draftees successfully")
                else:
                    await ctx.send("please use a csv")
            else:
                await ctx.send("please only send one file at a time")
        else:
            await ctx.send("please attach a csv")

@bot.command()
async def draftlist(ctx, draft_name: str = commands.parameter(default=None,description="-- name of the draft you're trying to list draftees for")):
    """
    lists the draftees in the draft
    example:
		$list draft_name
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name, "list")
    if user is None or draft_name is None:
        return
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    if len(draft_register[draft_id].draftees) > 0:
        headers = draft_register[draft_id].draftees[0].keys()
        data = {draftee.values() for draftee in draft_register[draft_id].draftees}
        table = tabulate(data, headers, tablefmt='grid')
        await ctx.send(f'```\n{table}\n```')
    else:
        await ctx.send("No draftees available.")

@bot.command()
async def execute(ctx, draft_name: str = commands.parameter(default=None,description="-- name of the draft you're trying to start"), round_count: int = commands.parameter(default=None, description="-- number of rounds to run the draft for")):
    """
    starts a draft
    only the owner of a draft can execute
    must include number of rounds; number of rounds is number each member of the draft will have at the end
    example:
		$execute draft_name round_count
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name, "execute")
    if user is None or draft_name is None:
        return
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    if await validate_authorAction(ctx, draft_name, ctx.author, "execute"):
        user, round_count = await is_notNegative(ctx, round_count, "round count", "execute (round)", True)
        if user is None or round_count is None:
            return
        if not await can_execute(ctx, draft_name, round_count):
            await ctx.send("insufficient number of draftees for the number of members")
            await ctx.send(f'(draftees: {len(draft_register[draft_id].draftees)}, member*round: {len(draft_register[draft_id].members)})*{round_count}={len(draft_register[draft_id].members)*round_count}')
            return
        draft_register[draft_id].order = await create_draftOrder(ctx, draft_name, round_count)
        draft_register[draft_id].status = "started"
        await send_message(ctx, draft_name, f'Draft order: {" -> ".join(member.name for member in draft_register[draft_name].order[0])}')
        draft = draft_register[draft_id]
        next_member = draft.order[draft.turn][0]
        await send_message(ctx, draft.name,f'it is <@{next_member.id}>\'s turn')

@bot.command()
async def roster(ctx, draft_name: str = commands.parameter(default=None,description="-- name of the draft you're trying to list a roster for"), member_id: str = commands.parameter(default=None, description="-- optional, the discord id of the draft member you want to see the roster for")):
    """
    reports the users's roster, or the roster of another user
    example:
		$roster draft_name [member_id]
    """
    global draft_register
    if member_id == None:
        member_id = ctx.author.id
    user, draft_name = await is_draft(ctx, draft_name, "retrieve roster")
    if user is None or draft_name is None:
        return
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    if len(draft_register[draft_id].members.member_id.roster) > 0:
        headers = draft_register[draft_id].members.member_id.roster[0].keys()
        data = {draftee.values() for draftee in draft_register[draft_id].members.member_id.roster}
        table = tabulate(data, headers, tablefmt='grid')
        await ctx.send(f'```\n{table}\n```')
    else:
        await ctx.send("No draftees in your roster.")

@bot.command()
async def draft(ctx, draft_name: str = commands.parameter(default=None,description="-- name of the draft you're trying to draft in"), draftee_id: int = commands.parameter(default=None,description="-- id of the draftee you're attempting to draft")):
    """
    drafts a draftee
    only the user who's turn it is can draft
    example:
		$draft draft_name draftee_id
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name, "draft")
    if user is None or draft_name is None:
        return
    user, draftee_id = await is_integer(ctx, draftee_id, "draftee", "draft draftee")
    if user is None or draftee_id is None:
        return
    user, draftee_id = await is_notNegative(ctx, draftee_id, "draftee", "draft draftee")
    if user is None or draftee_id is None:
        return
    draft_id = f'{draft_name}-{ctx.message.channel.id}'
    drafter = draft_register[draft_id].order[draft_register[draft_id].turn][0].name
    if user != drafter:
        logging.info(f'{user} attempted to draft in {draft_name} on {drafter}\'s turn')
        await ctx.message(f'it\'s {drafter}\'s turn, idiot')
    success = await draft_draftee(ctx, draft_name, draftee_id)
    if success is None:
        await ctx.send(f'ID {draftee_id} is not available in {draft_name}. please use `$list {draft_name}` to show the available draftees')
    
@bot.command()
async def sample(ctx):
    """
    attaches a sample csv file for filling out
    example:
		$sample
    """
    file = discord.File("./sample/sample.csv")
    await ctx.send("see attached csv", file=file)

@bot.command()
async def backup(ctx):
    """
    saves the draft register to a json file
    example:
		$backup
    """
    save_json()
    await ctx.send(f'draft register saved')

@bot.command()
async def test(ctx):
    """
    executes a test run
    example:
        $test
    """
    await ctx.send(f'$initiate testdraft')
    await initiate(ctx,"testdraft")
    await asyncio.sleep(2)
    await ctx.send(f'$sample')
    await sample(ctx)
    await asyncio.sleep(2)
    await ctx.send(f'$load testdraft')
    await load(ctx,"testdraft",True)
    await asyncio.sleep(2)
    await ctx.send(f'$draftlist testdraft')
    await draftlist(ctx,"testdraft")
    await asyncio.sleep(2)
    await ctx.send(f'$opt-out testdraft')
    await opt_out(ctx,"testdraft")
    await asyncio.sleep(2)
    await ctx.send(f'$opt-in testdraft')
    await opt_in(ctx,"testdraft")
    await asyncio.sleep(2)
    await ctx.send(f'$execute testdraft 2')
    await execute(ctx,"testdraft",2)
    await asyncio.sleep(2)
    await ctx.send(f'$draft testdraft 1')
    await draft(ctx,"testdraft",1)
    await asyncio.sleep(22)
    await ctx.send(f'$draftlist testdraft')
    await draftlist(ctx,"testdraft")
    await asyncio.sleep(2)
    await ctx.send(f'$draft testdraft 0')
    await draft(ctx,"testdraft",0)
    await asyncio.sleep(22)

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    command_list = "\n".join(command.name for command in bot.commands)
    await reply_all(f'***s***nake***d***raft***b***ot is ready to receive commands\n\n***valid commands:***\n```\n{command_list}\n```')
    logging.info(f'loading saved draft')
    load_json()
    bot.loop.create_task(timeCheck())
    bot.loop.create_task(turnCheck())
    bot.loop.create_task(draftCompleteCheck())

bot.run(TOKEN)