#chatgpt 3.5 helped start this
#prompt:
#   I need a discord bot coded with discord.py. The bot needs to be able to facilitate a snake draft. First, the person who initiates the draft should be identified as the commissioner. The commissioner should identify whether the draft is opt-in (all participants must enroll in the draft to be included) or opt-out (all users in the server are automatically enrolled, and must explicitly opt-out to not participate) when initiating the draft. Secondly, the commissioner should be able to load comma-delimited list of all available draftees. The comma-delimited list should require an ID field and a name field but also support an indeterminate number of fields. Third, the commissioner should be able to execute the draft. When the draft is executed, the commissioner identifies the number of rounds. The bot establishes a random draft order following snake draft order rules. The bot then notifies each user when it is their turn. The user can request a list of the current available draftees (in table format) and make a selection, at which point their turn ends. Any draftee selected by a user is removed from the list of available draftees and is recorded as being claimed by that user. Once all rounds have concluded, the bot outputs the draftees each user claimed.

#below is the initial output
#----------------------------------------------------------#
#import discord
#from discord.ext import commands
#import random
#
## Initialize bot
#bot = commands.Bot(command_prefix='!')
#
#@bot.event
#async def on_ready():
#    print(f'Bot is connected as {bot.user}')
#
## Define global variables
#commissioner = None
#opt_in = False
#draftees = []
#
#@bot.command()
#async def initiate_draft(ctx, draft_type):
#    global commissioner, opt_in, draftees
#    commissioner = ctx.author
#    opt_in = draft_type.lower() == 'opt-in'
#    # Load draftees (parse CSV, etc.)
#    # Set up draftees list
#
#@bot.command()
#async def execute_draft(ctx, num_rounds):
#    global commissioner, opt_in, draftees
#    # Randomize draft order (snake draft)
#    # Execute draft
#    # Notify users when it's their turn
#    # Allow users to make selections
#
#@bot.command()
#async def list_draftees(ctx):
#    global draftees
#    # Send a table of available draftees
#
#@bot.command()
#async def make_selection(ctx, selection):
#    global commissioner, draftees
#    # Record the selection, remove from available draftees
#
## Add more commands as needed
## Run the bot
#bot.run('YOUR_BOT_TOKEN')
#----------------------------------------------------------#
#csv prompt: back to the snake draft bot, can i pass an attachment through to a bot? if so, how would i pass a csv to the bot?

#@bot.command()
#async def load_draftees(ctx):
#    global draftees
#
#    # Check if there are attachments
#    if ctx.message.attachments:
#        attachment = ctx.message.attachments[0]  # Assuming only one attachment
#        if attachment.filename.endswith('.csv'):
#            # Download the file
#            await attachment.save(attachment.filename)
#
#            # Read and process the CSV file
#            with open(attachment.filename, 'r') as file:
#                reader = csv.reader(file)
#                for row in reader:
#                    # Assuming first column is ID and second column is Name
#                    id, name = row[0], row[1]
#                    draftees.append((id, name))
#
#            # Clean up by deleting the file
#            os.remove(attachment.filename)
#            await ctx.send("Draftees loaded successfully!")
#        else:
#            await ctx.send("Please provide a CSV file.")
#    else:
#        await ctx.send("Please attach a CSV file.")
#----------------------------------------------------------#
#prompt: how can i allow for an unknown number of columns in addition to the id and name column?

#@bot.command()
#async def load_draftees(ctx):
#    global draftees
#
#    if ctx.message.attachments:
#        attachment = ctx.message.attachments[0]
#        if attachment.filename.endswith('.csv'):
#            await attachment.save(attachment.filename)
#
#            with open(attachment.filename, 'r') as file:
#                reader = csv.DictReader(file)
#                for row in reader:
#                    id = row['ID']
#                    name = row['Name']
#                    other_fields = {key: value for key, value in row.items() if key not in ['ID', 'Name']}
#
#                    draftees.append({'ID': id, 'Name': name, **other_fields})
#
#            os.remove(attachment.filename)
#            await ctx.send("Draftees loaded successfully!")
#        else:
#            await ctx.send("Please provide a CSV file.")
#    else:
#        await ctx.send("Please attach a CSV file.")
#----------------------------------------------------------#
#list prompt: now that we've ingested the draftees, how can we list the draftees, and format the output in a table?

#from tabulate import tabulate
#
#@bot.command()
#async def list_draftees(ctx):
#    global draftees
#
#    if draftees:
#        headers = ['ID', 'Name'] + list(draftees[0].keys())[2:]  # Assuming first row is representative
#
#        # Extract relevant data
#        data = [[draftee['ID'], draftee['Name']] + list(draftee.values())[2:] for draftee in draftees]
#
#        # Format as a table and send
#        table = tabulate(data, headers, tablefmt='grid')
#        await ctx.send(f'```\n{table}\n```')
#    else:
#        await ctx.send("No draftees available.")
#----------------------------------------------------------#


import discord
from discord.ext import commands
import os
import csv
from tabulate import tabulate
import random


# pull token from file
TOKEN = open("token.txt","r").readline()

# establish intents for bot
intents = discord.Intents.default()
intents.members = True
intents.messages == True
intents.message_content = True
intents.guilds = True
intents.presences = True

# initialize bot
bot = commands.Bot(command_prefix='$',intents = intents)

# test command
@bot.command()
async def test(ctx):
    print("test")
    print(ctx.author)
    await ctx.message.channel.send("test received")
    pass

# global vars
draft_ids = []
draft_data = []

# input validation
async def validate_input(ctx, draft_id, action):
    user = str(ctx.author)
    if draft_id is None:
        print(user + " attempted to " + action + " without a value")
        await ctx.message.channel.send("please include a draft id when attempting to " + action)
        return None, None, None
    try:
        draft_id = int(draft_id)
    except ValueError:
        print(user + " input an invalid draft id")
        await ctx.message.channel.send("draft ids are numbers")
        return None, None, None
    str_draft_id = str(draft_id)
    return user,draft_id,str_draft_id

# check if there are enough draftees to execute the draft
def can_execute_draft(draft_id, num_rounds):
    global draft_data
    return len(draft_data[draft_id]["draftees"]) > len(draft_data[draft_id]["members"]) * num_rounds

# draft order
def create_draft_order(draft_id, num_rounds):
    global draft_data
    draft_order = []
    rd_draft_order = list(draft_data[draft_id]["members"])
    random.shuffle(rd_draft_order)
    i = 1
    draft_order.append(rd_draft_order)
    while i < num_rounds:
        rd_draft_order = list(reversed(rd_draft_order))
        draft_order.append(rd_draft_order)
        i += 1
    draft_data[draft_id]["order"].append(draft_order)
    return

# draft action
def draft_draftee(draft_id, draftee_id, member_id):
    global draft_ids, draft_data
    for i, draftee in enumerate(draft_data[draft_id]["draftees"]):
        if draftee['id'] == draftee_id:
            drafted = draft_data[draft_id]["draftees"].pop(i)
            draft_data[draft_id]["turn"] += 1
            draft_data[draft_id]["members"][member_id]["roster"].append(drafted)


#
# root commands
#

# $initiate (creates the draft)
@bot.command()
async def initiate(ctx, draft_type="None"):
    global draft_ids, draft_data
    user = str(ctx.author)
    opt_in = draft_type.lower() == 'opt-in'
    if opt_in == True:
        print(user + " has initiated an opt-in draft")
        members = []
    else:
        print(user + " has initiated a draft")
        members = [{'ID': str(ctx.author.id), 'Name': ctx.author.name, 'roster': [], 'data': member} for member in ctx.guild.members if not member.bot]

    draft_id = len(draft_ids)
    await ctx.message.channel.send("draft " + str(draft_id) + " initiated")
    await ctx.message.channel.send("please load a draftee list in csv format via $load")
    draft_ids.append(user)
    data = {
        'opt_in' : opt_in,
        'members' : members,
        'draftees': [],
        'order': [],
        'turn': 0
    }
    draft_data.append(data)
    return

@bot.command()
async def opt_in(ctx, draft_id=None):
    global draft_ids, draft_data
    user, draft_id, str_draft_id = await validate_input(ctx, draft_id, "opt-in")
    if user is None or draft_id is None or str_draft_id is None:
        return
    member_ids = {str(member.id) for member in draft_data[draft_id]["members"]}
    if str(ctx.author.id) in member_ids:
        await ctx.send("you've already opted in. if you want to opt back out, use $opt_out")
    else:
        new_member = [{'ID': str(ctx.author.id), 'Name': ctx.author.name, 'roster': [], 'data': ctx.author}]
        draft_data[draft_id]["members"].add(new_member)
        await ctx.send("you've been opted in")

@bot.command()
async def opt_out(ctx, draft_id=None):
    global draft_ids, draft_data
    user, draft_id, str_draft_id = await validate_input(ctx, draft_id, "opt-out")
    if user is None or draft_id is None or str_draft_id is None:
        return
    member_ids = {str(member.id) for member in draft_data[draft_id]["members"]}
    if str(ctx.author.id) in member_ids:
        new_member = [{'ID': str(ctx.author.id), 'Name': ctx.author.name, 'roster': [], 'data': ctx.author}]
        draft_data[draft_id]["members"].discard(new_member)
        await ctx.send("you've been opted out")
    else:
        await ctx.send("you've already opted out. if you want to opt back in, use $opt_in")

@bot.command()
async def cancel(ctx, draft_id=None):
    global draft_ids
    user, draft_id, str_draft_id = await validate_input(ctx, draft_id, "cancel")
    if user is None or draft_id is None or str_draft_id is None:
        return

    if draft_id < 0:
        print(user + " attempted to load a negative draft number")
        await ctx.message.channel.send("pls no underflow tyvm")
        return
    elif draft_id > len(draft_ids)-1:
        print(user + " attempted to cancel a draft that doesn't exist")
        await ctx.message.channel.send(str_draft_id + " hasn't been created yet")
        return
    elif draft_ids[draft_id] == "#cancelled":
        print(user + " attempted to cancel an already-cancelled draft")
        await ctx.message.channel.send(str_draft_id + " is already cancelled")
        return
    elif draft_ids[draft_id] == "#complete":
        print(user + " attempted to cancel an already-completed draft")
        await ctx.message.channel.send(str_draft_id + " is already complete")
        return
    elif isinstance(draft_id,int):
        if user == draft_ids[draft_id]:
            print(user + " has cancelled draft " + str_draft_id)
            await ctx.message.channel.send("draft " + str_draft_id + " has been cancelled")
            draft_ids[draft_id] = "#cancelled"
        else:
            print(user + " is attempting to cancel a draft initiated by " + draft_ids[draft_id])
            await ctx.message.channel.send("draft " + str_draft_id + " belongs to " + draft_ids[draft_id])

@bot.command()
async def load(ctx, draft_id=None):
    global draft_ids, draft_data
    user, draft_id, str_draft_id = await validate_input(ctx, draft_id, "load")
    if user is None or draft_id is None or str_draft_id is None:
        return

    if ctx.message.attachments:
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
                        draft_data[draft_id]["draftees"].append({'id':id,'name':name,**other_fields})
                os.remove(attachment.filename)
                await ctx.send("loaded draftees successfully")
            else:
                await ctx.send("please use a csv")
        else:
            await ctx.send("please only send one file at a time")
    else:
        await ctx.send("please attach a csv")

@bot.command()
async def list(ctx, draft_id=None):
    global draft_ids, draft_data
    user, draft_id, str_draft_id = await validate_input(ctx, draft_id, "list")
    if user is None or draft_id is None or str_draft_id is None:
        return

    if len(draft_data[draft_id]["draftees"]) > 0:
        headers = draft_data[draft_id]["draftees"][0].keys()
        data = {draftee.values() for draftee in draft_data[draft_id]["draftees"]}
        table = tabulate(data, headers, tablefmt='grid')
        await ctx.send(f'```\n{table}\n```')
    else:
        await ctx.send("No draftees available.")

@bot.command()
async def execute(ctx, draft_id=None, round_count=None):
    global draft_ids, draft_data
    user, draft_id, str_draft_id = await validate_input(ctx, draft_id, "execute (id)")
    if user is None or draft_id is None or str_draft_id is None:
        return
    user, round_count, str_draft_id = await validate_input(ctx, round_count, "execute (round)")
    if user is None or round_count is None or str_draft_id is None:
        return
    if round_count < 1:
        await ctx.send("round count must be greater than 1")
        return
    if not can_execute_draft(draft_id, round_count):
        ctx.send("insufficient number of draftees for the number of members")
        ctx.send("(" + str(len(draft_data[draft_id]["draftees"])) + "," + str(len(draft_data[draft_id]["members"])) + "*" + round_count + ")")
        return
    create_draft_order(draft_id, round_count)



@bot.command()
async def draft(ctx, draft_id=None, draftee_id=None):
    global draft_ids, draft_data

@bot.command()
async def sample(ctx):
    file = discord.File("./sample/sample.csv")
    await ctx.send("see attached csv", file=file)

bot.run(TOKEN)