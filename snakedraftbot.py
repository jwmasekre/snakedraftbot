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
from typing import List, Literal, NewType


# create the member and draft_data dataclasses
@dataclass
class Member:
    id: int
    name: str
    roster: List[dict]
    data: discord.Member

@dataclass
class DraftData:
    name: str
    opt_in: bool
    members: List[Member]
    draftees: List[dict]
    order: List[List[Member]]
    turn: int
    status: Literal["initiated","started","cancelled","completed"]
    prevTurn: int
    lastDraft: datetime
    owner: Member
    channel: int

# only global variables, the list of all drafts and the record of notifications
draft_register = {}
notif_record = {}

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
bot = commands.Bot(command_prefix='$',intents = intents,help_command = "draft_help")

# test command
@bot.command()
async def test(ctx):
    print(f'test from {ctx.author.name}')
    await ctx.send(f'@{ctx.author.id} test received :saluting_face:')

# input validation - is not negative
async def is_notNegative(ctx, val, valType, action, positive=False):
    user = ctx.author.name
    if positive:
        if val < 1:
            print(f'{user} attempted to {action} with a non-positive value for {valType}')
            return False
    elif val < 0:
        print(f'{user} attempted to {action} with a negative value for {valType}')
        return False
    else:
        return True

# input validation - draft name not already taken
async def validate_draftName(ctx, draft_name):
    user = ctx.author.name
    if draft_name in draft_register:
        print(f'{user} attempted to create a draft with name {draft_name}, which is already created')
        return False
    return True

# input validation - draft exists
async def is_draft(ctx, draft_name, action):
    user = ctx.author.name
    if draft_name not in draft_register:
        print(f'{user} attempted a {action} action for a draft that does not exist ({draft_name})')
        return False
    return True

# input validation - is integer
async def is_integer(ctx, val, valType, action):
    user = str(ctx.author)
    if val is None:
        print(f'{user} attempted to {action} without a value for {valType}')
        await ctx.send(f'please include a value for {valType} when attempting to {action}')
        return None, None
    try:
        val = int(val)
    except ValueError:
        print(f'{user} attempted to {action} with an invalid value for {valType}')
        await ctx.message.channel.send(f'{valType} must be an integer')
        return None, None
    return user,val

# input validation - draft actions & ownership
async def validate_authorAction(ctx, draft, author, action, authorOnly=False, noStart=False):
    user = str(author.name)
    if draft.status == "cancelled":
        print(f'{user} attempted to {action} an already-cancelled draft')
        await ctx.send(f'{draft.name} is already cancelled')
        return False
    elif draft.status == "completed":
        print(f'{user} attempted to {action} an already-completed draft')
        await ctx.send(f'{draft.name} is already complete')
        return False
    elif noStart:
        if draft.status == "started":
            print(f'{user} attempted to {action} an already-started draft')
            await ctx.send(f'{draft.name} is already started')
            return False
    elif authorOnly:
        if user == draft.owner:
            print(f'{user} attempted to {action} a draft initiated by {draft.owner}')
            await ctx.send(f'draft {draft.name} belongs to {draft.owner}, and only the draft owner can {action}')
            return False
    else:
        return True

# check if there are enough draftees to execute the draft
async def can_execute(draft, num_rounds):
    return len(draft.draftees) > len(draft.members) * num_rounds

# draft order
async def create_draftOrder(draft, num_rounds):
    draft_order = []
    rd_draft_order = list(draft.members)
    random.shuffle(rd_draft_order)
    i = 1
    draft_order.append(rd_draft_order)
    while i < num_rounds:
        rd_draft_order = list(reversed(rd_draft_order))
        draft_order.append(rd_draft_order)
        i += 1
    draft.order.append(draft_order)
    return

# draft action
async def draft_draftee(ctx, draft, draftee_id, member_id):
    user = ctx.author.name
    if draft.member_id.name != draft.order[draft.turn]:
        print(f'{user} attempted to draft on {draft.order[draft.turn]}\'s turn')
        await ctx.send(f'it\'s not your turn')
    for i, draftee in enumerate(draft.draftees):
        if draftee['id'] == draftee_id:
            drafted = draft.draftees.pop(i)
            draft.turn += 1
            draft.members.member_id.roster.append(drafted)
            now = datetime.datetime.now()
            draft_register[draft].lastDraft = now
            return
        else:
            i += 1
    return None

# reminds the current drafter to draft
async def timeCheck():
    global draft_register, notif_record
    while True:
        for draft in draft_register.values():
            now = datetime.datetime.now()
            then = draft.lastDraft
            if (now - then) > timedelta(hours=24) and draft.status == "started":
                current_drafter = draft.order[draft.turn]
                current_drafter_draft = f'{current_drafter} - {draft.name}'
                if current_drafter_draft in notif_record:
                    last = notif_record[current_drafter_draft]
                    if (now - last) > timedelta(hours=24):
                        print(f'notified {current_drafter.name} that they still need to pick')
                        reply_all(f'<@{current_drafter.id}, it\'s still your turn to draft')
                        notif_record[current_drafter_draft] = now
                        return
                else:
                    print(f'notified {current_drafter.name} that they still need to pick')
                    reply_all(f'<@{current_drafter.id}, it\'s still your turn to draft')
                    notif_record[current_drafter_draft] = now
        await asyncio.sleep(300)

async def draftCompleteCheck():
    global draft_register
    while True:
        for draft in draft_register.values():
            if (draft.status == "started") and (draft.turn >= len(draft.order)):
                send_message(f'a draft has completed')
                draft.status = "completed"
                printRoster(draft)
        await asyncio.sleep(300)

async def turnCheck():
    global draft_register
    while True:
        for draft in draft_register.values():
            if (draft.status == "started") and (draft.turn > draft.prevTurn):
                next_member = draft.order[draft.turn]
                send_message(draft,f'it is now @{next_member.id}\'s turn')
        await asyncio.sleep(300)

async def printRoster(ctx, draft):
    user = ctx.author.name
    print(f'printing roster for {user}')
    await ctx.send(f'{user}:\n\n{draft.ctx.author.id.roster}')

async def reply_all(message):
    for guild in bot.guilds:
        for channel in guild.text_channels:
            await channel.send(message)
            await asyncio.sleep(2)

async def send_message(draft, message):
    channel = bot.get_channel(draft.channel)
    if channel:
        await channel.send(message)
    else:
        print(f'could not find the channel for {draft.name}')


#
# bot commands
#


# $initiate (creates the draft)
@bot.command()
async def initiate(ctx, draft_name: str = commands.parameter(default=False, description="name of the new draft"), draft_type: str = commands.parameter(default="opt-out", description="optional, type 'opt-in' if you don't want your draft to automatically include everybody in the server")):
    """
    creates a new draft
    example:
		$initiate draft_name [opt-in]
    """
    global draft_register
    validate_draftName(ctx, draft_name)
    user = str(ctx.author)
    opt_in = draft_type.lower() == 'opt-in'
    if opt_in == True:
        print(f'{user} has initiated an opt-in draft, {draft_name}')
        members = []
    else:
        print(f'{user} has initiated a draft, {draft_name}')
        members = [Member(
            id = str(ctx.author.id),
            name = ctx.author.name,
            roster = [],
            data = member
        ) for member in ctx.guild.members if not member.bot]
    await ctx.message.channel.send(f'draft {draft_name} initiated')
    await ctx.message.channel.send(f'please load a draftee list in csv format via $load {draft_name}')
    now = datetime.datetime.now()
    data = DraftData(
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
    draft_register[draft_name] = data
    return

@bot.command()
async def opt_in(ctx, draft_name: str = commands.parameter(default=None, description="name of the draft you're trying to opt into")):
    """
    opts the user into a draft
    example:
		$opt_in draft_name
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name)
    if user is None or draft_name is None:
        return
    member_ids = {str(member.id) for member in draft_register[draft_name].members}
    if str(ctx.author.id) in member_ids:
        await ctx.send(f'you\'ve already opted in. if you want to opt back out, use $opt_out {draft_name}')
    else:
        new_member = Member(
            id = str(ctx.author.id),
            name =  ctx.author.name,
            roster = [],
            data =  ctx.author
        )
        draft_register[draft_name].members.append(new_member)
        await ctx.send(f'you\'ve been opted in to {draft_name}')

@bot.command()
async def opt_out(ctx, draft_name: str = commands.parameter(default=None, description="name of the draft you're trying to opt out of")):
    """
    opts the user out of a draft
    example:
		$opt_out draft_name
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name)
    if user is None or draft_name is None:
        return
    member_ids = {str(member.id) for member in draft_register[draft_name].members}
    if str(ctx.author.id) in member_ids:
        new_member = Member(
            id = str(ctx.author.id),
            name =  ctx.author.name,
            roster = [],
            data =  ctx.author
        )
        draft_register[draft_name].members.discard(new_member)
        await ctx.send(f'you\'ve been opted out of {draft_name}')
    else:
        await ctx.send(f'you\'ve already opted out. if you want to opt back in, use $opt_in {draft_name}')

@bot.command()
async def cancel(ctx, draft_name: str = commands.parameter(default=None,description="name of the draft you're trying to cancel")):
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
    if validate_authorAction(ctx, draft_name, ctx.author, "cancel"):
        print(user + " has cancelled draft " + draft_name)
        await ctx.send(f'draft {draft_name} has been cancelled')
        draft_register[draft_name].status = "cancelled"

@bot.command()
async def load(ctx, draft_name: str = commands.parameter(default=None,description="name of the draft you're trying to load draftees into"), test: bool = commands.parameter(default=False,description="used for testing, if you set this you're only causing problems")):
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
    if validate_authorAction(ctx, draft_name, ctx.author, "load"):
        if test == True:
            with open(".\\sample\\sample.csv",'r') as file:
                for row in reader:
                    id = row['id']
                    name = row['name']
                    other_fields = {key: value for key, value in row.items() if key not in ['id', 'name']}
                    draft_register[draft_name].draftees.append({'id':id,'name':name,**other_fields})
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
                            draft_register[draft_name].draftees.append({'id':id,'name':name,**other_fields})
                    os.remove(attachment.filename)
                    await ctx.send("loaded draftees successfully")
                else:
                    await ctx.send("please use a csv")
            else:
                await ctx.send("please only send one file at a time")
        else:
            await ctx.send("please attach a csv")

@bot.command()
async def list(ctx, draft_name: str = commands.parameter(default=None,description="name of the draft you're trying to list draftees for")):
    """
    lists the draftees in the draft
    example:
		$list draft_name
    """
    global draft_register
    user, draft_name = await is_draft(ctx, draft_name, "list")
    if user is None or draft_name is None:
        return
    if len(draft_register[draft_name].draftees) > 0:
        headers = draft_register[draft_name].draftees[0].keys()
        data = {draftee.values() for draftee in draft_register[draft_name].draftees}
        table = tabulate(data, headers, tablefmt='grid')
        await ctx.send(f'```\n{table}\n```')
    else:
        await ctx.send("No draftees available.")

@bot.command()
async def execute(ctx, draft_name: str = commands.parameter(default=None,description="name of the draft you're trying to start"), round_count: int = commands.parameter(default=None, description="number of rounds to run the draft for")):
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
    if validate_authorAction(ctx, draft_name, ctx.author, "execute"):
        user, round_count = await is_notNegative(ctx, round_count, "round count", "execute (round)", True)
        if user is None or round_count is None:
            return
        if not can_execute(draft_name, round_count):
            await ctx.send("insufficient number of draftees for the number of members")
            await ctx.send(f'( {len(draft_register[draft_name].draftees)}) , {len(draft_register[draft_name].members)}) * {round_count}')
            return
        create_draftOrder(draft_name, round_count)
        draft_register[draft_name].status = "started"

@bot.command()
async def roster(ctx, draft_name: str = commands.parameter(default=None,description="name of the draft you're trying to list a roster for"), member_id: str = commands.parameter(default=None, description="optional, the discord id of the draft member you want to see the roster for")):
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
    if len(draft_register[draft_name].members.member_id.roster) > 0:
        headers = draft_register[draft_name].members.member_id.roster[0].keys()
        data = {draftee.values() for draftee in draft_register[draft].members.member_id.roster}
        table = tabulate(data, headers, tablefmt='grid')
        await ctx.send(f'```\n{table}\n```')
    else:
        await ctx.send("No draftees in your roster.")

@bot.command()
async def draft(ctx, draft_name: str = commands.parameter(default=None,description="name of the draft you're trying to draft in"), draftee_id: int = commands.parameter(default=None,description="id of the draftee you're attempting to draft")):
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
    user, draftee_id = await is_integer(ctx, draftee_id, "draft draftee")
    if user is None or draftee_id is None:
        return
    user, draftee_id = await is_notNegative(ctx, draftee_id, "draft draftee")
    if user is None or draftee_id is None:
        return
    if ctx.author.name != draft_register[draft_name].ne:
        print()
    success = await draft_draftee(draft_name, draftee_id, ctx.author.id)
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
    await ctx.send(f'$list testdraft')
    await list(ctx,"testdraft")
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
    await asyncio.sleep(2)
    await ctx.send(f'$list testdraft')
    await list(ctx,"testdraft")
    await asyncio.sleep(300)
    await ctx.send(f'$draft testdraft 0')
    await draft(ctx,"testdraft",0)
    await asyncio.sleep(300)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    command_list = "\n".join(command.name for command in bot.commands)
    await reply_all(f'{bot.user.name} is ready to receive commands\n\n***valid commands:***\n{command_list}')
    await bot.loop.create_task(timeCheck())
    await bot.loop.create_task(turnCheck())
    await bot.loop.create_task(draftCompleteCheck())

bot.run(TOKEN)