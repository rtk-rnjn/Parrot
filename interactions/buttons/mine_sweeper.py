import discord
from discord.ext import commands
import random

class boardSpot(object):
    value = 0
    selected = False
    mine = False

    def __init__(self):
        self.selected = False

    def __str__(self):
        return str(boardSpot.value)

    def isMine(self):
        if boardSpot.value == -1:
            return True
        return False

class boardClass(object):
    def __init__(self, m_boardSize, m_numMines):
        self.board = [[boardSpot() for i in range(m_boardSize)] for j in range(m_boardSize)]
        self.boardSize = m_boardSize
        self.numMines = m_numMines
        self.selectableSpots = m_boardSize * m_boardSize - m_numMines
        i = 0
        while i < m_numMines:
            x = random.randint(0, self.boardSize - 1)
            y = random.randint(0, self.boardSize - 1)
            if not self.board[x][y].mine:
                self.addMine(x, y)
                i += 1
            else:
                i -= 1

    def __str__(self):
        returnString = " "
        divider = "\n---"

        for i in range(0, self.boardSize):
            returnString += " | " + str(i)
            divider += "----"
        divider += "\n"

        returnString += divider
        for y in range(0, self.boardSize):
            returnString += str(y)
            for x in range(0, self.boardSize):
                if self.board[x][y].mine and self.board[x][y].selected:
                    returnString += " |" + str(self.board[x][y].value)
                elif self.board[x][y].selected:
                    returnString += " | " + str(self.board[x][y].value)
                else:
                    returnString += " |  "
            returnString += " |"
            returnString += divider
        return returnString

    def addMine(self, x, y):
        self.board[x][y].value = -1
        self.board[x][y].mine = True
        for i in range(x - 1, x + 2):
            if i >= 0 and i < self.boardSize:
                if y - 1 >= 0 and not self.board[i][y - 1].mine:
                    self.board[i][y - 1].value += 1
                if y + 1 < self.boardSize and not self.board[i][y + 1].mine:
                    self.board[i][y + 1].value += 1
        if x - 1 >= 0 and not self.board[x - 1][y].mine:
            self.board[x - 1][y].value += 1
        if x + 1 < self.boardSize and not self.board[x + 1][y].mine:
            self.board[x + 1][y].value += 1

    def makeMove(self, x, y):
        self.board[x][y].selected = True
        self.selectableSpots -= 1
        if self.board[x][y].value == -1:
            return False
        if self.board[x][y].value == 0:
            for i in range(x - 1, x + 2):
                if i >= 0 and i < self.boardSize:
                    if y - 1 >= 0 and not self.board[i][y - 1].selected:
                        self.makeMove(i, y - 1)
                    if y + 1 < self.boardSize and not self.board[i][y + 1].selected:
                        self.makeMove(i, y + 1)
            if x - 1 >= 0 and not self.board[x - 1][y].selected:
                self.makeMove(x - 1, y)
            if x + 1 < self.boardSize and not self.board[x + 1][y].selected:
                self.makeMove(x + 1, y)
            return True
        else:
            return True

    def hitMine(self, x, y):
        return self.board[x][y].value == -1

    def isWinner(self):
        return self.selectableSpots == 0