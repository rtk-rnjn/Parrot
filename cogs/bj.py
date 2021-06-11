import asyncio
import random

import discord
from discord.ext import commands

suits = ("Hearts", "Diamonds", "Spades", "Clubs")
ranks = (
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Jack",
    "Queen",
    "King",
    "Ace",
)
values = {
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
    "Six": 6,
    "Seven": 7,
    "Eight": 8,
    "Nine": 9,
    "Ten": 10,
    "Jack": 10,
    "Queen": 10,
    "King": 10,
    "Ace": 11,
}

playing = True


class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __str__(self):
        # return self.rank + ' of ' + self.suit

        # self.rank + ' of ' + self.suit + ". value: " +
        return str(values[self.rank])


class Deck:
    def __init__(self):
        self.deck = []  # start with an empty list
        for suit in suits:
            for rank in ranks:
                self.deck.append(
                    Card(suit, rank)
                )  # build Card objects and add them to the list

    def __str__(self):
        deck_comp = ""  # start with an empty string
        for card in self.deck:
            deck_comp += "\n " + card.__str__()  # add each Card object's print string
        return "The deck has:" + deck_comp

    def shuffle(self):
        random.shuffle(self.deck)

    def deal(self):
        single_card = self.deck.pop()
        return single_card


class Hand:
    def __init__(self):
        self.cards = []  # start with an empty list as we did in the Deck class
        self.value = 0  # start with zero value
        self.aces = 0  # add an attribute to keep track of aces

    def add_card(self, card):
        self.cards.append(card)
        self.value += values[card.rank]
        if card.rank == "Ace":
            self.aces += 1  # add to self.aces

    def adjust_for_ace(self):
        while self.value > 21 and self.aces:
            self.value -= 10
            self.aces -= 1


class Chips:
    def __init__(self):
        self.total = (
            100  # This can be set to a default value or supplied by a user input
        )
        self.bet = 0

    def win_bet(self):
        self.total += self.bet

    def lose_bet(self):
        self.total -= self.bet


# Functions
def take_bet():
    return "How many chips would you like to bet? "


def hit(deck, hand):
    hand.add_card(deck.deal())
    hand.adjust_for_ace()


def hit_or_stand(deck, hand, x):
    global playing  # to control an upcoming while loop

    while True:
        # input h or s

        if x[0].lower() == "h":
            hit(deck, hand)  # hit() function defined above

        elif x[0].lower() == "s":

            playing = False
            return "Player stands. Dealer is playing."

        else:
            continue
            # return "Sorry, please try again."

        break


def show_some(player, dealer):
    print("\nDealer's Hand:")
    print(" <card hidden>")
    print("", dealer.cards[1])
    print("\nPlayer's Hand:", *player.cards, sep="\n ")


def show_all(player, dealer):
    print("\nDealer's Hand:", *dealer.cards, sep="\n ")
    print("Dealer's Hand =", dealer.value)
    print("\nPlayer's Hand:", *player.cards, sep="\n ")
    print("Player's Hand =", player.value)


def player_busts(player, dealer, chips):
    print("Player busts!")
    chips.lose_bet()


def player_wins(player, dealer, chips):
    print("Player wins!")
    chips.win_bet()


def dealer_busts(player, dealer, chips):
    print("Dealer busts!")
    chips.win_bet()


def dealer_wins(player, dealer, chips):
    print("Dealer wins!")
    chips.lose_bet()


def push(player, dealer):
    print("Dealer and Player tie! It's a push.")


class Bj(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.round_number = 0

    @commands.command(name="blackjack")
    async def _Bj(self, ctx):
        while True:
            self.round_number += 1
            # Print an opening statement
            await ctx.channel.send(
                "Welcome to BlackJack! Get as close to 21 as you can without going over!\n\
            Dealer hits until she reaches 17. Aces count as 1 or 11.\n"
            )

            # Create & shuffle the deck, deal two cards to each player
            deck = Deck()
            deck.shuffle()

            player_hand = Hand()
            player_hand.add_card(deck.deal())
            player_hand.add_card(deck.deal())

            dealer_hand = Hand()
            dealer_hand.add_card(deck.deal())
            dealer_hand.add_card(deck.deal())

            # Set up the Player's chips
            player_chips = Chips()  # remember the default value is 100

            # Prompt the Player for their bet
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            await ctx.channel.send(take_bet())
            try:
                msg = await self.client.wait_for("message", timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Please answer within 30 seconds")
            else:
                if int(msg.content) > player_chips.total:
                    await ctx.send("Sorry, your bet can't exceed", player_chips.total)
                else:
                    player_chips.bet = int(msg.content)

            # Show cards (but keep one dealer card hidden)
            embed = discord.Embed(
                title="Round {}".format(self.round_number), colour=discord.Colour.blue()
            )

            dealer_cards = (
                " <card hidden>\n"
                + str(dealer_hand.cards[1])
                + "\nTotal: "
                + str(dealer_hand.cards[1])
            )
            embed.add_field(name="Dealer's Hand:", value=dealer_cards)

            player_cards = ""
            total = 0
            for x in player_hand.cards:
                player_cards += str(x) + "\n"
                total += int(str(x))
            player_cards += "Total: " + str(total)

            embed.add_field(name="Player's Hand:", value=player_cards)
            await ctx.send(embed=embed)

            first_time = True
            global playing
            while playing:  # recall this variable from our hit_or_stand function
                if not first_time:
                    self.round_number += 1
                first_time = False
                # Prompt for Player to Hit or Stand

                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel

                await ctx.channel.send(
                    "Would you like to Hit or Stand? Enter 'h' or 's' "
                )
                try:
                    msg = await self.client.wait_for(
                        "message", timeout=30.0, check=check
                    )
                except asyncio.TimeoutError:
                    await ctx.send("Please answer within 30 seconds")
                else:
                    hit_or_stand(deck, player_hand, msg.content)

                # Show cards (but keep one dealer card hidden)
                embed = discord.Embed(
                    title="Round {}".format(self.round_number + 1),
                    colour=discord.Colour.blue(),
                )

                dealer_cards = (
                    " <card hidden>\n"
                    + str(dealer_hand.cards[1])
                    + "\nTotal: "
                    + str(dealer_hand.cards[1])
                )
                embed.add_field(name="Dealer's Hand:", value=dealer_cards)

                player_cards = ""
                total = 0
                for x in player_hand.cards:
                    player_cards += str(x) + "\n"
                    total += int(str(x))
                player_cards += "Total: " + str(total)

                embed.add_field(name="Player's Hand:", value=player_cards)
                await ctx.send(embed=embed)

                # If player's hand exceeds 21, run player_busts() and break out of loop
                if player_hand.value > 21:
                    player_busts(player_hand, dealer_hand, player_chips)
                    break

                    # If Player hasn't busted, play Dealer's hand until Dealer reaches 17
            if player_hand.value <= 21:

                while dealer_hand.value < 17:
                    hit(deck, dealer_hand)

                    # Show all cards
                embed = discord.Embed(title="Round Ended", colour=discord.Colour.blue())

                dealer_cards = ""
                for i in dealer_hand.cards:
                    dealer_cards += str(i) + " "
                embed.add_field(name="Dealer's Hand:", value=dealer_cards)

                player_cards = ""
                total = 0
                for x in player_hand.cards:
                    player_cards += str(x) + " "
                    total += int(str(x))
                player_cards += "Total: " + str(total)
                embed.add_field(name="Player's Hand:", value=player_cards)
                await ctx.send(embed=embed)

                # Run different winning scenarios
                if dealer_hand.value > 21:
                    dealer_busts(player_hand, dealer_hand, player_chips)
                elif dealer_hand.value > player_hand.value:
                    dealer_wins(player_hand, dealer_hand, player_chips)
                elif dealer_hand.value < player_hand.value:
                    player_wins(player_hand, dealer_hand, player_chips)
                else:
                    push(player_hand, dealer_hand)
                    # Inform Player of their chips total

            await ctx.channel.send(
                "\nPlayer's winnings stand at" + str(player_chips.total)
            )

            # Ask to play again
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            await ctx.channel.send(
                "Would you like to play another hand? Enter 'y' or 'n' "
            )
            try:
                msg = await self.client.wait_for("message", timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Please answer within 30 seconds")
            else:
                if msg.content[0].lower() == "y":
                    playing = True
                    continue
                else:
                    print("Thanks for playing!")
                    break


def setup(client):
    client.add_cog(Bj(client))
