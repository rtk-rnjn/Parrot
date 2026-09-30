from cogs.misc.logo.interpreter import LogoInterpreter
from cogs.misc.logo.parser import LogoParser

source = """
TO SQUARE :SIZE
    REPEAT 4 [FD :SIZE RT 90]
END

SETPC "RED
SETWIDTH 5
SQUARE 200
"""


parser = LogoParser()
program = parser.parse(source)

interpreter = LogoInterpreter()
interpreter.execute(program)

image = interpreter.turtle.render()

with open("output.png", "wb") as file:
    file.write(image.read())
