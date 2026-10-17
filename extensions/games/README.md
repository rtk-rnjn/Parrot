# Games

Interactive Discord games with message, reaction, and component-based interfaces.

## Included games

Akinator, Battleship, Blackjack, Boggle, Chess, Connect Four, Hangman, 2048, Memory, Number Memory, Sokoban, Tictactoe, UNO, Wordle, and more.

## Card table games

Teen Patti, Texas Hold'em, Hearts and Bluff share one framework in `games/card_core.py`:

- A **lobby** with a Join Game button. The host starts the game and empty seats are filled with bots, so you can play solo against the AI.
- A public **table image** (felt, seats, pile, played cards) edited in place as the game progresses.
- A private **My Hand** panel per player with the buttons and card picker for the current decision. Players who time out twice are played by the bot.
- One table per channel at a time.

Game assets and game-specific helpers live under this package.