import os
import random

from PIL import Image, ImageFont, ImageDraw
import mysql.connector
from mysql.connector import Error


def generateBoard(rows=5, cols=5):
    # import word bank
    word_bank_file = open("words.txt", "r")
    word_list = word_bank_file.read().splitlines()
    random.shuffle(word_list)

    # select board cards
    board_words = word_list[:24]
    death_card = word_list[50]
    team_cards = random.sample(board_words, 9)
    board_words += [death_card]
    random.shuffle(board_words)

    # generate board
    board = [[0]*cols for row in range(rows)]
    ind = 0
    for row in range(rows):
       for col in range(cols):
           board[row][col] = board_words[ind]
           ind+=1

    return board, team_cards, board_words, death_card


def runQuery(query, return_result=True):
    conn = mysql.connector.connect()
    if conn.is_connected():
        cursor = conn.cursor()
        cursor.execute(query)
        if return_result:
            try:
                results = cursor.fetchall()[0]
                conn.close()
                return results
            except:
                conn.close()
                return None

    conn.commit()
    conn.close()
    return None


def update_guesses(user, correct):
    query_retrieve = "SELECT * from guesses where user_id = '%s'" %(user)
    current_stats = runQuery(query_retrieve)

    # insert new user
    if current_stats == None:
        # insert new users
        print("not in database atm lol")
        query_update = "INSERT INTO guesses(user_id, correct_guesses, incorrect_guesses) VALUES ('%s', %s, %s)"
        if correct:
            args = (user, 1, 0)
        else:
            args = (user, 0, 1)

    # update existing user
    else:
        if correct:
            query_update = "UPDATE guesses SET correct_guesses = %s WHERE user_id = '%s'"
            args = (current_stats[1]+1, user)
        else: 
            query_update = "UPDATE guesses SET incorrect_guesses = %s WHERE user_id = '%s'"
            args = (current_stats[2]+1, user)

    runQuery(query_update %args, False)


def return_stats(user):
    query_retrieve = "SELECT * from guesses where user_id = '%s'" %(user)
    results = runQuery(query_retrieve)
    str_results = '**Stats for user:** %s\nCorrect guesses: %d\nIncorrect guesses: %d' %(results[0], results[1], results[2])
    return str_results


class CodenamesGame():
    def __init__(self, clues=6):
        self.clues = clues
        self.board, self.team_cards, self.all_cards, self.death_card = generateBoard()
        self.picked_cards = []
        self.errors = 0
        self.cards_left = 9
        self.found_cards = []
        self.missed_cards = []
        self.spymaster = None
        self.guesses = 0
        self.clue = None
        self.past_clues = []
        self.board_image = "img.png"
        self.spy_image = "spy.png"
        self.makeImage()
        self.makeSpyImage()


    # from: https://github.com/joaoperfig/discordBoggle
    def makeImage(self):
        image = Image.new("RGBA", (1000,500), (36,84,99))
        font = ImageFont.truetype("futurab.otf", 20)
        y = 50
        for row in self.board:
            x = 100
            for word in row:     
                draw = ImageDraw.Draw(image)
                # found death card
                if word in self.found_cards and word == self.death_card:
                    draw.rectangle(((x-90, y-45), (x+90, y+45)), fill=(90,90,90))
                # found card
                elif word in self.found_cards:
                    draw.rectangle(((x-90, y-45), (x+90, y+45)), fill=(60,179,113))
                # missed card
                elif word != self.death_card and word in self.missed_cards:
                    draw.rectangle(((x-90, y-45), (x+90, y+45)), fill=(240,128,128))
                else: draw.rectangle(((x-90, y-45), (x+90, y+45)), fill=(50,139,158))
                draw = ImageDraw.Draw(image)
                w,h = draw.textsize(word.upper(), font=font)
                draw = draw.text((x-(w/2),y-(h/2)), word.upper(),(235,235,235), font=font)
                x += 200
            y += 100   
        image.save(self.board_image)


    def makeSpyImage(self):
        image = Image.new("RGBA", (1000,500), (36,84,99))
        font = ImageFont.truetype("futurab.otf", 20)
        y = 50
        for row in self.board:
            x = 100
            for word in row:     
                draw = ImageDraw.Draw(image)
                if word == self.death_card:
                    draw.rectangle(((x-90, y-45), (x+90, y+45)), fill=(90,90,90))
                elif word in self.team_cards and word not in self.found_cards:
                    draw.rectangle(((x-90, y-45), (x+90, y+45)), fill=(240,128,128))
                elif word in self.found_cards or word in self.missed_cards:
                    draw.rectangle(((x-90, y-45), (x+90, y+45)), fill=(222,207,179))
                else: draw.rectangle(((x-90, y-45), (x+90, y+45)), fill=(50,139,158))
                draw = ImageDraw.Draw(image)
                w,h = draw.textsize(word.upper(), font=font)
                draw = draw.text((x-(w/2),y-(h/2)), word.upper(),(235,235,235), font=font)
                x += 200
            y += 100   
        image.save(self.spy_image)


    def setSpymaster(self, spymaster_user, spymaster_id):
        self.spymaster = spymaster_user
        self.spymaster_id = spymaster_id


    def giveClue(self, clue, guesses):
        self.guesses = guesses+1
        self.clue = clue
        self.past_clues += [self.clue]
        self.clues -= 1


    def pickCard(self, picked_card, user):
        correct_guess = False

        if picked_card in self.picked_cards or picked_card not in self.all_cards:
            return 'unavailable'

        elif picked_card == self.death_card:
            self.found_cards += [picked_card]
            self.errors += 1
            self.guesses = 0
            self.makeImage()
            update_guesses(user, correct_guess)
            return 'death'

        else:
            self.picked_cards += [picked_card]
            self.guesses -= 1
            for row in self.board:
                for card in row:
                    if card == picked_card:
                        if picked_card in self.team_cards:
                            self.cards_left -= 1
                            correct_guess = True
                            self.found_cards += [picked_card]
                            self.makeImage()
                            self.makeSpyImage()

            update_guesses(user, correct_guess)

            if self.cards_left == 0:
                return 'game_complete'

            elif correct_guess:
                if self.guesses > 0:
                    return 'turn_continues'
                elif self.clues > 0:
                    return 'next_clue'
                else:
                    return 'correct_but_game_lost'

            self.missed_cards += [picked_card]
            self.errors += 1
            self.guesses = 0
            self.clue = None
            self.makeImage()
            self.makeSpyImage()

            if self.clues > 0:
                return 'turn_lost'

            return 'incorrect_and_game_lost'


    def gameOver(self):
        self.clues = 0
        self.picked_cards = []
        self.errors = 0
        self.cards_left = 9
        self.spymaster = None
        self.guesses = 0
        self.clue = 0
        self.past_clues = []
        self.found_cards = []
        self.missed_cards = []
