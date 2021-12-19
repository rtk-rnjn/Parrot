import os
import copy

class Level:

    matrix = []
    matrix_history = []
    
    def __init__(self,set,level_num):
        
        del self.matrix[:]
        del self.matrix_history[:]
        
        # Create level
        with open(os.path.dirname(os.path.abspath(__file__)) + '/levels/' + set + '/level' + str(level_num), 'r') as f:
                for row in f.read().splitlines():
                    self.matrix.append(list(row))
            
    def __del__(self):
        "Destructor to make sure object shuts down, etc."
        
    def getMatrix(self):
        return self.matrix

    def addToHistory(self,matrix):
        self.matrix_history.append(copy.deepcopy(matrix))

    def getLastMatrix(self):
        if len(self.matrix_history) > 0:
            lastMatrix = self.matrix_history.pop()
            self.matrix = lastMatrix
            return lastMatrix
        else:
            return self.matrix

    def getPlayerPosition(self):
        # Iterate all Rows
        for i in range (0,len(self.matrix)):
            # Iterate all columns
            for k in range (0,len(self.matrix[i])-1):
                if self.matrix[i][k] == "@":
                    return [k,i]

    def getBoxes(self):
        # Iterate all Rows
        boxes = []
        for i in range (0,len(self.matrix)):
            # Iterate all columns
            for k in range (0,len(self.matrix[i])-1):
                if self.matrix[i][k] == "$":
                    boxes.append([k,i])
        return boxes

    def getSize(self):
        max_row_length = 0
        # Iterate all Rows
        for i in range (0,len(self.matrix)):
            # Iterate all columns
            row_length = len(self.matrix[i])
            if row_length > max_row_length:
                max_row_length = row_length
        return [max_row_length,len(self.matrix)]