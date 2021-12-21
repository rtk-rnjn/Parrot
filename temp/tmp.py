

import random



        

  


game = Twenty48(a)
game.start()
self=game
while True:
    x = input()
    if x == 'd':
        self.MoveRight()

    elif x == 'a':
        self.MoveLeft()

    elif x == 's':
        self.MoveDown()

    elif x == 'w':
        self.MoveUp()

    self.spawn_new()
    BoardString = self.number_to_emoji()
    print(BoardString)