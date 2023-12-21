import psycopg2
import bcrypt
import interactions
import hashlib
import os
import struct
import configparser
import asyncio  # Add this line to import asyncio
from interactions import Client, Intents, listen
from interactions import slash_command, SlashContext
from interactions import Embed, ContextMenuContext, Message, message_context_menu
from interactions import user_context_menu, Member
from interactions import OptionType, slash_option
from interactions.api.events import MessageReactionAdd  # or any other event
from interactions import Button, ButtonStyle
from interactions.api.events import Component
from interactions.ext.paginators import Paginator

# Read configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Get database authentication details from config.ini
DB_HOST = config.get('Credentials', 'DB_HOST')
DB_NAME = config.get('Credentials', 'DB_NAME')
DB_USER = config.get('Credentials', 'DB_USER')
DB_PASSWORD = config.get('Credentials', 'DB_PASSWORD')

# Get bot token from config.ini
BOT_TOKEN = config.get('Credentials', 'BOT_TOKEN')

# Establish PostgreSQL connection
conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

TOKEN = BOT_TOKEN
#TOKEN = 'MTE2NjMzODQ3Nzk0MDU1MTcyMg.G8SXss.DwcmuuakARmCVaDC6ms_OIHqLEskDJJSc8D6GQ'
bot = interactions.Client()

def readArmorData(binary_data):

    if len(binary_data) < 0x70:
        return 0

    offsets = [0x2E, 0x3E, 0x4E, 0x5E, 0x6E, 0x7E, 0x2C]

    values_list = []
    for offset in offsets:
        index = offset
        uint16_value = struct.unpack_from('<H', binary_data, index)[0]
        #print(format(uint16_value, '04X'))
        values_list.append(uint16_value)

    file_paths = [
    os.path.join('data', 'melee.txt'),
    os.path.join('data', 'legs.txt'),
    os.path.join('data', 'head.txt'),
    os.path.join('data', 'chest.txt'),
    os.path.join('data', 'arms.txt'),
    os.path.join('data', 'waist.txt'),
    os.path.join('data', 'ranged.txt')
    ]
    print(file_paths[0])
    # Function to parse the data file and extract keys and values
    def parse_data_file(parts, svalue):
        #file_paths = ['melee.txt', 'legs.txt', 'head.txt', 'chest.txt', 'arms.txt', 'waist.txt',  'ranged.txt']
        if values_list[6] != 0x0601 and parts == 0:
            parts = 6
        svalue = format(svalue, '04X')

        with open(file_paths[parts], 'r', encoding = 'utf-8') as file:
            for line in file:
                try:
                    key, value = map(str.strip, line.split(' => '))

                except ValueError as e:
                    print("Problem")

                else:
                    key = key.strip("'")  # Remove single quotes from the key
                    #parsed_data[key] = value

                if key == svalue:
                    return value
                    break

    armor_list = []
    for index, armor_data in enumerate(values_list[:-1]):
        armor_list.append(parse_data_file(index, values_list[index]))

    return armor_list

    for armor_data in armor_list:
        print(armor_data)

def generate_file(username, password):

    sha256 = hashlib.sha256()
    sha256.update(password.encode('utf-8'))
    hashed_password = sha256.hexdigest()

    account_data = """\
AccountInstance_00000000
PersistentId=80000001
TransferableIdBase=0
Uuid=b1e7bd03ced3441a8a0cf82f826d6054
MiiData=03000040e955a209e7c74182dbfba88003b3b88d27d90000004077006100740074006100670065007200000000004040000021010268441826344614811217680d00002900524850000000000000000000000000000000000000000000007e37
MiiName=00770061007400740061006700650072000000000000
AccountId=""" + username + """
BirthYear=0
BirthMonth=0
BirthDay=0
Gender=0
EmailAddress=temporarydata@temp.com
Country=0
SimpleAddressId=0
PrincipalId=4642aa83
IsPasswordCacheEnabled=1
AccountPasswordCache="""+ hashed_password

    return account_data

def get_user_password(username):
    cursor = conn.cursor()

    # Retrieve the hashed password for the provided username
    query = "SELECT password FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    password = cursor.fetchone()

    cursor.close()

    if password:
        return password[0]
    else:
        return None

def register_new_account(discord_id, username, password):
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s', (username,))
    checkUsername = cursor.fetchone()[0]

    if checkUsername == 0:
        # Generate a bcrypt hash of the password
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        try:
                # Insert the username and hashed password into the database
            query1 = "INSERT INTO users (username, password) VALUES (%s, %s)"
            cursor.execute(query1, (username, hashed_password))
        
            query2 = "INSERT INTO characters (user_id, is_female, is_new_character, name, unk_desc_string,hrp, gr, weapon_type, last_login) VALUES ((select id from users where username = %s), %s,%s, %s,%s, %s,%s, %s,%s)"
            cursor.execute(query2, (username, False, True, '', '', 0, 0, 0, 0))

            query3 = "INSERT INTO discord_data (discord_id, user_id) VALUES (%s, (SELECT id FROM users WHERE username = %s))"
            cursor.execute(query3, (discord_id, username))
        
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return 2

        finally:
            cursor.close()
            #conn.close()
            return 1
    else:
        cursor.close()
        #conn.close()
        return 0

#INSERT INTO discord (discord_id, user_id) VALUES (123456789, (SELECT id FROM users WHERE username = 'XXX'));
    

def add_new_character(username, password):
    stored_password = get_user_password(username)
    if stored_password:
        if bcrypt.checkpw(password.encode(), stored_password.encode()):
            try:
                cursor = conn.cursor()
                query = "INSERT INTO characters (user_id, is_female, is_new_character, name, unk_desc_string,hrp, gr, weapon_type, last_login) VALUES ((select id from users where username = %s), %s,%s, %s,%s, %s,%s, %s,%s)"
                cursor.execute(query, (username, False, True, '', '', 0, 0, 0, 0))

                conn.commit()
                cursor.close()
                return 1
                #await ctx.send(f"New Characters has been successfully created.", ephemeral=True)
            except Exception as e:
                conn.rollback()
                print(f"Error: {e}")

            finally:
                cursor.close()
                #conn.close()
        else:
            return 0
            #await ctx.send("Add new characters fail. Invalid username or password.", ephemeral=True)
    else:
        return 0
        #await ctx.send("failed. Invalid username or password.", ephemeral=True)

@slash_command(name="link", description="link Account")
@slash_option(
    name="username",
    description="input your username",
    required=True,
    opt_type=OptionType.STRING,
    min_length=4,
    max_length=10
)
@slash_option(
    name="password",
    description="input your password",
    required=True,
    opt_type=OptionType.STRING,
    min_length=4,
    max_length=10
)
async def link_command_function(ctx: SlashContext, username: str, password: str):
    stored_password = get_user_password(username)
    if stored_password:
        if bcrypt.checkpw(password.encode(), stored_password.encode()):
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM discord_data WHERE discord_id = %s', (ctx.author.id,))
                check = cursor.fetchone()

                if check[0] == 0:      
                    linkquery = "INSERT INTO discord_data (discord_id, user_id) VALUES (%s, (SELECT id FROM users WHERE username = %s))"
                    cursor.execute(linkquery, (ctx.author.id, username))

                    conn.commit()
                    await ctx.send("Succesfully Linked an Account")
                    return 1
                else:
                    await ctx.send("You already have an account Linked")
                #await ctx.send(f"New Characters has been successfully created.", ephemeral=True)
            except Exception as e:
                conn.rollback()
                print(f"Error: {e}")

            finally:
                cursor.close()
                #conn.close()
        else:
            print("Password Not Match")
            await ctx.send("Wrong Username/Password")
            return 0
            #await ctx.send("Add new characters fail. Invalid username or password.", ephemeral=True)
    else:
        print(F"No account with username {username}")
        await ctx.send("Wrong Username/Password")
        return 0
        #await ctx.send("failed. Invalid username or password.", ephemeral=True)

@slash_command(name="bind", description="Bind Account")
@slash_option(
    name="username",
    description="input your username",
    required=True,
    opt_type=OptionType.STRING,
    min_length=4,
    max_length=10
)
@slash_option(
    name="password",
    description="input your password",
    required=True,
    opt_type=OptionType.STRING,
    min_length=4,
    max_length=10
)
# @slash_option(
#     name="wii_account_id",
#     description="input your wii ultimate account ID",
#     required=True,
#     opt_type=OptionType.STRING,
#     min_length=1,
#     max_length=20
# )
# @slash_option(
#     name="wii_password_cache",
#     description="input your wii ultimate cached password",
#     required=True,
#     opt_type=OptionType.STRING,
#     min_length=1,
#     max_length=64
# )
# async def bind_command_function(ctx: SlashContext, username: str, password: str, wii_account_id: str, wii_password_cache: str):
#     stored_password = get_user_password(username)
#     if stored_password:
#         if bcrypt.checkpw(password.encode(), stored_password.encode()):
#             combine = wii_account_id + wii_password_cache

#             hash_object = hashlib.sha256(combine.encode())
#             token = hash_object.hexdigest()[:64]

#             cursor = conn.cursor()
#             cursor.execute('SELECT COUNT(*) FROM users WHERE wiiu_key = %s', (token,))
#             count = cursor.fetchone()[0]

#             if count == 0:
#                 query = "UPDATE users set wiiu_key = %s where username = %s"
#                 cursor.execute(query, (token,username))
#                 await ctx.send(f"Your Wii U key '{token}' \nhas been successfully registered.", ephemeral=True)
#             else:
#                 await ctx.send(f"The Wii U key is already registered.", ephemeral=True)

#             conn.commit()
#             cursor.close()
#         else:
#             await ctx.send("Bind failed. Invalid username or password.", ephemeral=True)
#     else:
#         await ctx.send("Bind failed. Invalid username or password.", ephemeral=True)

async def bind_command_function(ctx: SlashContext, username: str, password: str):
    stored_password = get_user_password(username)
    if stored_password:
        if bcrypt.checkpw(password.encode(), stored_password.encode()):
            hashpass = hashlib.sha256()
            hashpass.update(password.encode('utf-8'))
            combine = username + hashpass.hexdigest()

            hash_object = hashlib.sha256(combine.encode())
            token = hash_object.hexdigest()[:64]

            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE wiiu_key = %s', (token,))
            count = cursor.fetchone()[0]

            if count == 0:
                query = "UPDATE users set wiiu_key = %s where username = %s"
                cursor.execute(query, (token,username))
                await ctx.send(f"Your Wii U key ```'{token}'``` \nhas been successfully registered.\n", ephemeral=True)
                #text_content = "Hello World"
                #file = discord.File(text_content.encode(), filename="hello.txt")
                #file_obj = io.StringIO(generate_file(username,password))
                # Send the text as a file
                custom_filename = f"{username}_account.dat"
                # Create the file with the custom name
                with open(custom_filename, 'w') as file:
                    file.write(generate_file(username,password))
                   
                await ctx.send(f"To Start Playing:\n1. Rename the '{username}_account.dat' into account.dat\n2. Put the file inside cemu\\mlc01\\usr\\save\\system\\act\\80000001\\", file=custom_filename, ephemeral=True)
                #await ctx.send(file=generate_file(username,password), filename='file.txt')
                os.remove(custom_filename)

            else:
                await ctx.send(f"The Wii U key is already registered.", ephemeral=True)

            conn.commit()
            cursor.close()
        else:
            await ctx.send("Bind failed. Invalid username or password.", ephemeral=True)
    else:
        await ctx.send("Bind failed. Invalid username or password.", ephemeral=True)

@slash_command(name="register", description="create account first")
@slash_option(
    name="username",
    description="Input Username",
    required=True,
    opt_type=OptionType.STRING,
    min_length=4,
    max_length=16
)
@slash_option(
    name="password",
    description="Input Password",
    required=True,
    opt_type=OptionType.STRING,
    min_length=4,
    max_length=16
)
async def register_command_function(ctx: SlashContext, username: str, password: str):
    Password = password.encode('utf-8')
    salt = bcrypt.gensalt()  # Generate a random salt
    hashed_password = bcrypt.hashpw(Password, salt)
    #hashed_password = bcrypt.hashpw(password)
    # Query the database for the user
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM discord_data WHERE discord_id = %s', (ctx.author.id,))
    count = cursor.fetchone()[0]

    if count == 0:
        reg = register_new_account(ctx.author.id,username,password)
        if reg == 0:
            await ctx.send(f"Account with username : `{username}` \nAlready Exist.", ephemeral=True)
        elif reg == 1:
            await ctx.send(f"Account with username : `{username}` \nhas been successfully created.", ephemeral=True)
        elif reg == 2:
            await ctx.send(f"Failed To Create Account, Error in the Query", ephemeral=True)
    else:
        cursor.execute('SELECT users.username FROM discord_data JOIN users ON discord_data.user_id = users.id WHERE discord_data.discord_id = %s', (ctx.author.id,))
        name = cursor.fetchone()[0]
        await ctx.send(f"You already registered with username '{name}'", ephemeral=True)
    cursor.close()

@slash_command(name="add_characters", description="create account first")
@slash_option(
    name="username",
    description="Input Username",
    required=True,
    opt_type=OptionType.STRING,
    min_length=4,
    max_length=16
)
@slash_option(
    name="password",
    description="Input Password",
    required=True,
    opt_type=OptionType.STRING,
    min_length=4,
    max_length=16
)
async def add_characters_command_function(ctx: SlashContext, username: str, password: str):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(c.user_id) AS user_id_count FROM characters AS c INNER JOIN users AS u ON c.user_id = u.id WHERE u.username = %s', (username,))
    count = cursor.fetchone()[0]
    if count < 3:
        success = add_new_character(username,password)
        if(success == 0):
            await ctx.send("Add new characters fail. Invalid username or password.", ephemeral=True)
        else:
            await ctx.send(f"New Characters has been successfully created.", ephemeral=True)
    else:
        await ctx.send(f"Account with username '{username}' already Have 3 Characters", ephemeral=True)
    cursor.close()

@slash_command(name="ping", description="Check me")
async def ping_command_function(ctx: SlashContext):
    sender_id = ctx.author.id
    await ctx.send(f'Hello World\nYour Discord ID is: {sender_id}')


# @slash_command(name="guildcard", description="Check me")
# async def guildcard_command_function(ctx: SlashContext):
#     cursor = conn.cursor()
#     cursor.execute('SELECT id,name,hrp,time_played,gcp,netcafe_points from characters where user_id = (select user_id from discord_data where discord_id = %s)', (ctx.author.id,))
#     gc = cursor.fetchall()

#     if gc is None:
#         await ctx.send("You're not registered")
#         return

#     for row in gc:
#          #print(f"No: {no}, Name: {name}")
#         charid = str(row[0])
#         name = row[1]
#         hrp = str(row[2])
#         playtime = str(row[3])
#         np = str(row[4])
#         gcp = str(row[5])

#         embed = Embed(
#         title="My Guild Card",
#         description="ID       : "+ charid +"\nName     : "+ name +"\nHR       : "+ hrp +"\nPlaytime : "+playtime+"\nN Points : "+np+"\nGCP      : " + gcp ,
#         )
#         await ctx.send(embeds=embed)


@slash_command(name="contract", description="Contract Mercenary")
@slash_option(
    name="hunterid",
    description="Input Desired Hunter Name to be contracted",
    required=True,
    opt_type=OptionType.STRING,
    min_length=1,
    max_length=10
)
async def contract_command_function(ctx: SlashContext, hunterid: str):
    button = Button(
        custom_id="my_button_id",
        style=ButtonStyle.GREEN,
        label="Accept",
    )
    
    sender_id = ctx.author.id
    cursor = conn.cursor()
    #cursor.execute('select discord_id, discord_data.user_id, name from discord_data inner join characters on characters.user_id = discord_data.user_id where characters.name = %s', (hunter,))
    cursor.execute('select count(pact_id) from characters where pact_id = (select rasta_id from characters where id = %s)', (hunterid,))
    isfull = cursor.fetchone()
    if isfull is not None:
        if isfull[0] > 2:
            await ctx.send("Sorry, The Hunter you're trying to contract is already has 3 contracts", ephemeral=True)
            return

    cursor.execute('select name, savemercenary, rasta_id, discord_id from characters inner join discord_data on characters.user_id = discord_data.user_id where characters.id = %s', (hunterid,))
    mercenData = cursor.fetchone()
    #agreement_message = await ctx.send(f'Hello World\nYour Discord ID is: {sender_id} and Your User_id is {discordID}', components=button)
    #cursor.close()

    if mercenData is not None:
        # Assuming result[0] contains the bytea data
        pactuser = await bot.fetch_user(mercenData[3])
        abinary_data = mercenData[1]
        equipment = readArmorData(abinary_data)
        for armor_data in equipment:
            print(armor_data)
        
        # embed = Embed(
        # title="Mercenary Contract\n\nHunter : " + mercenData[0] + "\n",
        # description="\n<:gs:1174293910273658961> : "+ equipment[0] +"\n<:helm:1174160247049424958> : "+ equipment[2] +"\n<:chest:1174161014267322440> : "+ equipment[3] +"\n<:arm:1174162638142459965> : "+ equipment[4] +"\n<:waist:1174162059529830531> : "+ equipment[5] +"\n<:greave:1174162450170511431> : " + equipment[1] +"\n\nPlease ask the person you wish to contract with to press the 'Accept' button.",
        # color=0xF0F0F0,
        # )
        embed = Embed(
        title=f"Mercenary Contract"
              f"\nHunter : {mercenData[0]}",
        description=f"\n\n<:gs:1174293910273658961>: {equipment[0]}"
                    f"\n<:helm:1174160247049424958>: {equipment[2]}"
                    f"\n<:chest:1174161014267322440>: {equipment[3]}"
                    f"\n<:arm:1174162638142459965>: {equipment[4]}"
                    f"\n<:waist:1174162059529830531>: {equipment[5]}"
                    f"\n<:greave:1174162450170511431>: {equipment[1]}"
                    f"\n\nPlease ask the person you wish to contract with to press the 'Accept' button."
                    f" the Button Will be expires in 30 Seconds",
        color=0xF0F0F0
)
        embed.set_thumbnail(pactuser.avatar_url)
    else :
        embed = Embed(
        title="No Rasta data with Hunter :",
        description="Fail to Contract" ,
        )
        
    agreement_message = await ctx.send(embeds=embed, components=button)
    
    # define the check
    async def check(component: Component) -> bool:
        if component.ctx.author == ctx.author:
            await component.ctx.send("You cant contract yourself!", ephemeral=True)
        elif component.ctx.author.id == mercenData[3]:
            return True
        else:
            await component.ctx.send("This button is not for you!", ephemeral=True)

    try:
        used_component: Component = await bot.wait_for_component(components=button, check=check, timeout=30)

    except asyncio.TimeoutError:
        print("Timed Out!")

        button.disabled = True
        await agreement_message.edit(components=button)

    else:
        try:
            query = "UPDATE characters set pact_id = %s where user_id = (select user_id from discord_data where discord_id = %s)"
            cursor.execute(query, (mercenData[2],ctx.author.id))
            conn.commit()
            await used_component.ctx.send(F"Congratulation!!!, Pact has been made between {ctx.author} and {pactuser}")

        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")

        finally:
            cursor.close()
            #conn.close()

        button.disabled = True
        await agreement_message.edit(components=button)

@user_context_menu(name="guildcard")
async def guildcard_contex_menu(ctx: ContextMenuContext):
    member: Member = ctx.target
    cursor = conn.cursor()
    cursor.execute('SELECT id,name,hrp,time_played,gcp,netcafe_points,is_new_character from characters where user_id = (select user_id from discord_data where discord_id = %s)', (ctx.target.id,))
    gc = cursor.fetchall()

    if gc is None:
        await ctx.send("You're not registered")
        return

    embeds = []
    for row in gc:
         #print(f"No: {no}, Name: {name}")
        charid = str(row[0])
        name = row[1]
        hrp = str(row[2])
        playtime = str(row[3])
        np = str(row[4])
        gcp = str(row[5])

        if row[6] == 0:
            embed = Embed(
            title="Guild Card",
            #description="ID\t: "+ charid +"\nName     : "+ name +"\nHR       : "+ hrp +"\nPlaytime : "+playtime+"\nN Points : "+np+"\nGCP      : " + gcp ,
            color=0x3498db,
            )
            embed.add_field(name = 'ID', value= charid, inline = False)
            embed.add_field(name = 'Name', value = name, inline = True)
            embed.add_field(name = 'HR', value = hrp, inline = True)
            embed.add_field(name = 'GCP', value = gcp, inline = True)
            embed.add_field(name = 'N Point', value = np, inline = True)
            embed.add_field(name = 'Playtime', value = playtime, inline = True)
            embeds.append(embed)
        else:
            embed = Embed(
            title="Guild Card",
            #description="ID\t: "+ charid +"\nName     : "+ name +"\nHR       : "+ hrp +"\nPlaytime : "+playtime+"\nN Points : "+np+"\nGCP      : " + gcp ,
            color=0x3498db,
            )
            embed.add_field(name = 'ID', value= charid, inline = False)
            embed.add_field(name = 'Name', value = "New Save", inline = True)
            embed.add_field(name = 'HR', value = "0", inline = True)
            embed.add_field(name = 'GCP', value = "0", inline = True)
            embed.add_field(name = 'N Point', value = "0", inline = True)
            embed.add_field(name = 'Playtime', value = "0", inline = True)
            embeds.append(embed)

        #await ctx.send(embeds=embed)
    cursor.close()
    #embeds = [Embed("Page 1 content"), Embed("Page 2 embed"), Embed("Page 3 embed"), Embed("Page 4 embed")]
    if len(embeds) > 0:
        paginator = Paginator.create_from_embeds(bot, *embeds) 
        paginator.show_first_button=False
        paginator.show_last_button=False
        await paginator.send(ctx)
    else:
        await ctx.send(F"No Data from {ctx.target}")
    #await ctx.send(member.mention)

@interactions.listen()
async def on_startup():
    print("Bot is ready!")

# @interactions.listen(MessageReactionAdd)
# async def an_event_handler(event: MessageReactionAdd):
#     if user == event.author and str(event.emoji) == '\N{THUMBS UP SIGN}' and reaction.message.id == agreement_message.id:
#         print(f"{event.author} react with {event.emoji}")

bot.start(TOKEN)