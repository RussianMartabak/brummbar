import discord, os, logging, pomice, asyncio


from wikif import getWikiPage
from helper import songList
from discord.ext import commands

# the global variable for the lavalink node
HOST = 'lavalink.oops.wtf'
PASS = 'www.freelavalink.ga'
PORT = 2000



playing = False
logging.basicConfig(level=logging.CRITICAL, format=' %(asctime)s - %(levelname)s - %(message)s')
class MyBot(commands.Bot):
    def __init__(self) -> None:
        watching = discord.Activity(type=discord.ActivityType.watching, name='for !p to play music')
        intent = discord.Intents.default()
        intent.message_content = True
        super().__init__(command_prefix='!', activity=watching, intents=intent)
        self.help_command = None
        

    async def on_ready(self) -> None:
        await self.add_cog(Misc(self))
        await self.add_cog(Music(self))
        logging.critical('i\'m ready')
        music = self.get_cog('Music')
        await music.start_nodes()





class Misc(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.songs = []
    
    @commands.command(aliases=['s'])
    async def sieg(self, ctx: commands.Context):
        await ctx.send('Heil!')

    @commands.command(aliases=['w'])
    async def wiki(self, ctx: commands.Context, *, input: str):
        wikiPage = getWikiPage(input)
        if wikiPage:
            logging.critical('there is a wikiPage')
            url = wikiPage.fullurl
            summary = wikiPage.summary
            if len(summary) > 4095:
                summary = summary[0:4095]
            title = wikiPage.title
            logging.critical(title)
            embed = discord.Embed(title=title, url=url, description=summary, colour=discord.Color.purple())
            try:
                await ctx.send(embed=embed)
                return
            except BaseException as err:
                logging.critical(err)
        await ctx.send('No wiki page found on that term')

    
    @commands.command(aliases=['h'])
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(title="Commands", description="""This is all kinds of commands you can use. 
        Its honestly pretty barebone right now, but I will add more features in some time.
        """, color=discord.Color.purple())
        embed.add_field(name="!p + <keyword>", value="Use this command to play an audio from Youtube. e.g `!p panzelied`", inline=False)
        embed.add_field(name="(!q or !query) + <keyword>", value="Use this command to search Youtube, it will return top 5 entry that matched", inline=False)
        embed.add_field(name="!stop", value="Use this command to stop, clear all playlist and disconnect the bot", inline=False)
        embed.add_field(name='(!playlist or !pl)', value="Use this command to see the current playlist", inline=False)
        embed.add_field(name='(!loop or !l)', value="Use this command to enable Brummbar to loop the playlist", inline=False)
        embed.add_field(name="(!nowplaying or !np)", value="Use this command to see the current track and its duration", inline=False)
        embed.add_field(name= "!skip", value="Use this command to skip currently playing track", inline=False)

        await ctx.send(embed=embed)

class Music(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.pomice = pomice.NodePool()
        self.i = 0 #for indexing
        self.trackList = []
        self.vc = []
    async def start_nodes(self):
        await self.pomice.create_node(bot=self.bot, host=HOST, port=PORT, identifier='nazi', password=PASS, spotify_client_id=None, spotify_client_secret=None)
        logging.critical("node ready")
    
    def findsongList(self, guild): #function to find songList object for the server
        for songlist in self.trackList:
            if songlist.guild == guild:
                return songlist
        return None

    def milisecToMinutes(self, milisec): #return dict of times
        outputDict = {
            'seconds': 0,
            'minutes': 0
        }
        rawSec = int(milisec / 1000)
        seconds = rawSec % 60
        minutes = int((rawSec - seconds) / 60)
        
        formattedSeconds = str(seconds)
        formattedMinutes = str(minutes)
        if seconds < 10:
            formattedSeconds = '0' + formattedSeconds
        outputDict['seconds'] = formattedSeconds
        
        outputDict['minutes'] = formattedMinutes
        return outputDict
    
    def findVoiceClient(self, guild): #return the voice client in the server/guild
        for VClient in self.bot.voice_clients:
                if VClient.guild == guild:
                    
                    logging.critical(f'vclient found: {VClient}')
                    return VClient
        return None


    
    @commands.Cog.listener()
    #listen if bot disconnected
    async def on_voice_state_update(self, member, before, after):
        logging.critical(f"the member: {member} changed, {before.channel} -> {after.channel}")
        try: 
            functionGuild = before.channel.guild
        except: 
            functionGuild = None
        if member == self.bot.user and after.channel == None:
            
            #find the voiceclient 
            VClient = self.findVoiceClient(functionGuild)
            await VClient.destroy()
            
            
    
    
    
    
    @commands.Cog.listener()
    #add 1 to i when a player start a track
    async def on_pomice_track_start(self, player, track):
        logging.critical(f'{track} is starting')
        playlist = self.findsongList(player.guild)
        if playlist:
            playlist.index += 1

    @commands.command()
    async def seek(self, ctx: commands.Context, *, minutes: str):
        try:
            minutes = float(minutes)
            #convert minutes to milisec
            milisec = minutes * 60000
            #get the current track's room to manuever
            player = self.findVoiceClient(ctx.guild)
            if player: #if bot is playing
                room = (player.current.length - player.position) - milisec
                if room > 0 and milisec > 0:
                    await player.seek(milisec)
                    await ctx.send(f'**Forwarded** `{minutes} minutes into the future`')
                else:
                    await ctx.send('you seek too much')
            else:
                await ctx.send('not playing')
                    
        except:
            await ctx.send('Must be a number')

    @commands.command(aliases=['query'])
    async def q(self, ctx: commands.Context, *, search: str):
        try:
            player = self.vc[0]
        except:
            ctx.send("bot not connected yet")
            return
        results = await player.get_tracks(query=f'{search}')
        if results:
            await ctx.send("**Tracks Found: **")
            limit = min(len(results), 5)
            limit += 1
            for i in range(1, limit):
                await ctx.send(f"`{i}. {results[i].title}`")
        else:
            ctx.send("not found or bot isn't connected to vc yet")

    @commands.command(aliases=['l'])
    async def loop(self, ctx: commands.Context):
        localSongList = self.findsongList(ctx.guild)
        if localSongList:
            if localSongList.loop == False:
                localSongList.loop = True
                await ctx.send('**Loop Enabled**')
            else:
                localSongList.loop = False
                await ctx.send('**Loop Disabled**')

    @commands.command()
    async def skip(self, ctx: commands.Context):
        player = self.findVoiceClient(ctx.guild)
        await player.stop()

    @commands.command(aliases=['pl'])
    async def playlist(self, ctx: commands.Context):
        localSongList = self.findsongList(ctx.guild)
        i = 0
        if localSongList:
            await ctx.send('**Currently Playlist:**')
            for song in localSongList.songs:
                i += 1
                await ctx.send(f'`{i}. {song.title}`')
        else:
            await ctx.send('There is no playlist')
    #now playing will return current track and the position + duration
    @commands.command(aliases=['np'])
    async def nowplaying(self, ctx: commands.Context):
        localGuild = ctx.guild
        
        player = self.findVoiceClient(localGuild)
        try:
            track = player.current
            title = track.title
            duration = track.length
            logging.critical(duration)
            ftime = self.milisecToMinutes(duration) #dict or the total duration
            currentPosition = player.position
            fcurrentPosition = self.milisecToMinutes(currentPosition)
            currentMinutes = fcurrentPosition['minutes']
            currentSeconds = fcurrentPosition['seconds']
            print(ftime)
            totalMinutes = ftime['minutes']
            totalSeconds = ftime['seconds']
            await ctx.send('**Currently Playing:**')
            await ctx.send(f'`{title}; {currentMinutes}:{currentSeconds} - {totalMinutes}:{totalSeconds}`')

        except BaseException as err:
            logging.critical(err)
            await ctx.send('currently not playing anything')
            


    @commands.command(aliases=['play'])
    async def p(self, ctx: commands.Context, *, search: str):
        #make bot join and check if it already joined a vc
        
        if search:
            try:
                #is it in the vc user in?
                logging.critical('the try is invoked')
                vc = ctx.author.voice.channel
                
                #if bot is not in the vc
                if not self.bot.user in vc.members:
                    
                    VClient = await vc.connect(cls=pomice.Player)
                    
                    guildSongList = songList(VClient.guild)
                    self.trackList.append(guildSongList)
                    self.vc.append(VClient)
                #if bot already in vc
                else : 
                    VClient = self.findVoiceClient(ctx.guild)
                    guildSongList = self.findsongList(ctx.guild)
                
                
                if not guildSongList:
                    guildSongList = songList(VClient.guild)
                    self.trackList.append(guildSongList)
                logging.critical(VClient.is_playing)
                results = await VClient.get_tracks(query=f'{search}')
                
                if results and VClient.is_playing == False:
                        
                    await VClient.play(track=results[0])
                    guildSongList.add(results[0])
                    music = str(results[0].title)
                    thumbnail = str(results[0].uri)
                    #track announcer
                    logging.critical(results)
                    await ctx.send(f"**Playing** `{music}`")
                    
                    return   
                        
                elif results:
                    guildSongList.add(results[0])
                    await ctx.send(f"**Added** `{results[0].title}` to queue")
                    logging.critical(guildSongList.songs)

                else: 
                    await ctx.send('either no results or bot is still playing')
                    
            except BaseException as err:
                await ctx.send("you are not in a voice channel")
                logging.critical(f"exception occured {err}")
    

    @commands.command()
    async def stop(self, ctx: commands.Context):
        
        
        for vc in self.bot.voice_clients:
            if vc.is_playing and vc.guild==ctx.guild:
                playlist = self.findsongList(vc.guild)
                await vc.stop()
                if playlist:
                    self.trackList.remove(playlist)
                break
     
    @commands.Cog.listener()
    async def on_pomice_track_end(self, player, track, reason):
        #check list and play next song in list
        #reset index if its already maximum
        #find the correct songlist in self.tracklist 
        logging.critical("a player has stopped playing track")
        if player.is_playing:
            await player.stop()
        playlist = self.findsongList(player.guild)
        try: #this is the mechanism to play through the playlist ot looping
            await player.play(playlist.songs[playlist.index])
            logging.critical(f'current index is {playlist.index}')
        except: 
            try:
                if playlist.loop == True:
                    playlist.index = 0
                    await player.play(playlist.songs[0])
            except:
                logging.critical('no next song')
        await asyncio.sleep(20)
        if not player.is_playing:
            if playlist:
                self.trackList.remove(playlist)
                playlist.index = 0
            await player.destroy()
        logging.critical(player.current)
        logging.critical(track)
        logging.critical(reason)
        
    
               #break
TOKEN = os.getenv("TOKEN")
bot = MyBot()
bot.run(TOKEN)
