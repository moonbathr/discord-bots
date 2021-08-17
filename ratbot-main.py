import discord
from codenames_game import *

import os.path
from os import path
import re
import random
import glob

import spacy
from spacy.lang.en.examples import sentences 
import markovify
import nltk
from nltk.corpus import gutenberg
import warnings

#utility function for text cleaning
def text_cleaner(text):
    text = re.sub(r'--', ' ', text)
    text = re.sub('[\[].*?[\]]', '', text)
    #text = re.sub(r'(\b|\s+\-?|^\-?)(\d+|\d*\.\d+)\b','', text)
    text = ' '.join(text.split())
    #text = text.replace("/", "");
    #text = text.replace("<", "");
    #text = text.replace(">", "");
    text = text.replace("@", " ");
    text = text.replace(" . ", " ");
    return text

def deEmojify(text):
    regrex_pattern = re.compile(pattern = "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags = re.UNICODE)
    return regrex_pattern.sub(r'',text)

class CodenamesBot(discord.Client):
    async def on_ready(self):
        print('We have logged in as {0.user}'.format(self))

    async def create_game(self, message):
        game_mode = message.content.split('&start game ')[1]
        if game_mode in ['easy', 'medium', 'hard']:
            clues_per_mode = {'easy': 6, 'medium': 5, 'hard': 4}
            self.game = CodenamesGame(clues_per_mode[game_mode])
            await message.channel.send('Game started! Clear all nine cards within %d clues.\nSet yourself as spymaster with `&spymaster`.' %self.game.clues)
            await message.channel.send(file=discord.File(self.game.board_image))
        else:
            await message.channel.send('Invalid game mode.')


    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('&start game '):
            # if existing game, only current spymaster or ratmin can refresh
            try:
                if (self.game.spymaster == None) or (self.game.spymaster == str(message.author)):
                    await self.create_game(message)
                else:
                    await message.channel.send('A game is already running.')
            except:
                await self.create_game(message)

        if message.content.startswith('&board'):
            await message.channel.send(file=discord.File(self.game.board_image))

        if message.content.startswith('&spymaster'):
            if self.game.spymaster == None:
                self.game.setSpymaster(str(message.author), message.author.id)
                await message.channel.send('Spymaster set: ' + self.game.spymaster + '. Clue format: `&clue place, 5`.')
                await message.author.send(file=discord.File(self.game.spy_image))
                await message.author.send("These are your words: " + ', '.join(self.game.team_cards))
                await message.author.send("This is the death card: " + self.game.death_card)
            else:
                await message.channel.send('Spymaster already set: ' + self.game.spymaster)

        if message.content.startswith('&clue'):
            if self.game.clues > 0:
                if self.game.spymaster == str(message.author):
                    try:
                        guesses = int(message.content.split(', ')[1])
                        clue = message.content.split('&clue ')[1].split(',')[0].split(' ')[0]
                        await message.delete()
                        self.game.giveClue(clue, guesses)
                        await message.channel.send('**Clue:** ' + self.game.clue + '\n**Guesses:** ' + str(self.game.guesses-1) + '\nPlayers can select cards with `&pick word`.')
                        await message.channel.send(file=discord.File(self.game.board_image))
                    except:
                        await message.channel.send('Invalid clue format. Example format: `&clue city, 3`')
                else:
                    await message.channel.send("Hey! You're not the spymaster =|")

        if message.content.startswith('&pick'):
            if self.game.guesses > 0:
                picked_card = message.content.split('&pick ')[1].lower()
                turn_result = self.game.pickCard(picked_card, str(message.author))
                turn_responses = {'unavailable': 'Card unavailable on the board.',
                               'death': 'OH NO. You picked the death card. GAME OVER!',
                               'turn_continues': 'You found one! There are still %d guesses remaining this turn.' %(self.game.guesses),
                               'next_clue': 'Clue successfully decoded! This turn is complete.',
                               'correct_but_game_lost': 'GAME OVER. You lost. You found the right card...but there are no clues left.',
                               'turn_lost': "Oops! That wasn't your card! This turn has ended.",
                               'incorrect_and_game_lost': "GAME OVER. That wasn't your card, and you're outta turns.",
                               'game_complete': 'WOOOO CODENAMES WOOOOOOO!!! You did it! Board cleared.'}
                await message.channel.send(turn_responses[turn_result])
                await message.channel.send(file=discord.File(self.game.board_image))
                if 'GAME OVER' in turn_responses[turn_result] or 'WOOO' in turn_responses[turn_result]:
                    self.game.gameOver()
                user = await client.fetch_user(int(self.game.spymaster_id))
                await user.send(file=discord.File(self.game.spy_image))

        if message.content.startswith('&skip'):
            self.game.guesses = 0
            await message.channel.send("Turn ended.")

        if message.content.startswith('&end game'):
            role = discord.utils.get(message.guild.roles, name="ratmin")
            if (self.game.spymaster == str(message.author)):
                await message.channel.send('Game ended.')
                self.game.gameOver()
            elif role in message.author.roles:
                await message.channel.send('Game ended.')
                self.game.gameOver()


        if message.content.startswith('&game stats'):
            if self.game.board != None:
                await message.channel.send("**Current clue:** " + str(self.game.clue) 
                    + "\n**Guesses remaining this turn:** " + str(max(0, self.game.guesses-1)) 
                    + "\n**Past clues:** " + ', '.join(self.game.past_clues) 
                    + "\n**# clues remaining:** " + str(self.game.clues) 
                    + "\n**Mistakes:** " + str(self.game.errors)
                    + "\n**Total cards left:** " + str(self.game.cards_left))

        if message.content.startswith('&my stats'):
            await message.channel.send(return_stats(str(message.author)))


        # HELP COMMANDS
        if message.content == '&help':
            await message.channel.send("`&help codenames` for codenames info; `&help bot me` for bot me info.")

        if message.content.startswith('&help codenames'):
            message_text = ("`&start game [easy/medium/hard]` to start a game with 6, 5, 4 guesses.\n"
                "`&spymaster` to set yourself as spymaster.\n"
                "`&clue [one word clue], #` to submit clue\n"
                "`&pick [card]` to pick a card\n"
                "`&end turn` to end a turn\n"
                "`&eng game` to end game (spymaster & admin only)\n"
                "`&game stats` for game stats\n"
                "`&my stats` for your stats")
            await message.channel.send(message_text)

        if message.content.startswith('&help bot me'):
            message_text = ("`&bot me` looks at your last 3k messages in a channel, and generates a fake message from you.\n"
                "The first time you call the bot in a channel, wait a minute or so for it to work.")
            await message.channel.send(message_text)
    

        # BOT ME
        if message.content.startswith('&bot me'):
            file_name = "data_%s_%s.txt" %(str(message.author), str(message.channel))

            other_user = None

            if not path.exists(file_name) or message.content.startswith('&bot me ow'):
                text = ""
                async for msg in message.channel.history(limit=3000):
                    if msg.author == message.author and not (msg.content.startswith('&bot me')):
                        text = msg.content + ". " + text
                
                text = text_cleaner(text)
                text = deEmojify(text)
                text_file = open(file_name, "w", encoding='utf-8')
                n = text_file.write(text)
                text_file.close()

            else:
                with open(file_name,'r', encoding='utf-8') as file:
                    text = file.read()


                if message.content.startswith('&bot me rand'):
                    #os.chdir(r'directory where the files are located')
                    myFiles = glob.glob('*%s.txt' %(str(message.channel)))
                    myFiles.remove(file_name)
                    if len(myFiles) >= 1:
                        second_file = myFiles[random.randint(0,len(myFiles)-1)]

                        with open(second_file,'r', encoding='utf-8') as file:
                            text = text + " " + file.read()
                            other_user = second_file.split('#')[0][5:]


            nlp = spacy.load('en_core_web_sm')
            text_doc = nlp(text)
            text_sents = ' '.join([sent.text for sent in text_doc.sents if len(sent.text) > 1])
            generator_1 = markovify.Text(text_sents, state_size=2)
            sentence = generator_1.make_sentence()

            attempts_left = 5
            if sentence is None:
                generator_1 = markovify.Text(text_sents, state_size=1)
                while sentence is None and attempts_left > 0:
                    sentence = generator_1.make_sentence()
                    attempts_left -= 1

            if sentence is not None:
                if len(sentence) > 500:
                    try:
                        sent_list = sentence.split(".")
                        new_text = sent_list[random.randint(0,len(sent_list)-1)]
                        sentence = new_text
                    except:
                        print("oops")
                if other_user is not None:
                    sentence = "**" + str(message.author).split('#')[0] + " & " + other_user +"**: " + sentence
                else:
                    sentence = "**" + str(message.author).split('#')[0] + "**: " + sentence
                await message.channel.send(sentence)
            else:
                await message.channel.send("try talking more before trying to bot yourself tbh.........")

client = CodenamesBot()
client.run('')
