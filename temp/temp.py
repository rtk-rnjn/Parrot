
import time
import sys
from Environment import Environment
from Level import Level

def drawLevel(matrix_to_draw):
	
	# Load level images
	wall = ":white_large_square:"
	box = ":soccer:"
	box_on_target =  ":red_square:"
	space = ":black_large_square:"
	target = ":o:"
	player = ":flushed:"
	
	# If horizontal or vertical resolution is not enough to fit the level images then resize images
	if myLevel.getSize()[0] > myEnvironment.size[0] / 36 or myLevel.getSize()[1] > myEnvironment.size[1] / 36:
		
		# If level's x size > level's y size then resize according to x axis
		if myLevel.getSize()[0] / myLevel.getSize()[1] >= 1:
			new_image_size = myEnvironment.size[0]/myLevel.getSize()[0]
		# If level's y size > level's x size then resize according to y axis
		else:
			new_image_size = myEnvironment.size[1]/myLevel.getSize()[1]
		
		# Just to the resize job	
		wall = pygame.transform.scale(wall, (new_image_size,new_image_size))
		box = pygame.transform.scale(box, (new_image_size,new_image_size))
		box_on_target = pygame.transform.scale(box_on_target, (new_image_size,new_image_size))
		space = pygame.transform.scale(space, (new_image_size,new_image_size))
		target = pygame.transform.scale(target, (new_image_size,new_image_size))
		player = pygame.transform.scale(player, (new_image_size,new_image_size))	
		
	# Just a Dictionary (associative array in pyhton's lingua) to map images to characters used in level design 
	images = {'#': wall, ' ': space, '$': box, '.': target, '@': player, '*': box_on_target}
	
	# Get image size. Images are always squares so it doesn't care if you get width or height
	box_size = wall.get_width()
	
	# Iterate all Rows
	for i in range (0,len(matrix_to_draw)):
		# Iterate all columns of the row
		for c in range (0,len(matrix_to_draw[i])):
			myEnvironment.screen.blit(images[matrix_to_draw[i][c]], (c*box_size, i*box_size))

	pygame.display.update()
				
def movePlayer(direction,myLevel):
	
	matrix = myLevel.getMatrix()
	
	myLevel.addToHistory(matrix)
	
	x = myLevel.getPlayerPosition()[0]
	y = myLevel.getPlayerPosition()[1]
	
	global target_found
	
	#print boxes
	print  myLevel.getBoxes()
	
	if direction == "L":
		print "######### Moving Left #########"
		
		# if is_space
		if matrix[y][x-1] == " ":
			print "OK Space Found"
			matrix[y][x-1] = "@"
			if target_found == True:
				matrix[y][x] = "."
				target_found = False
			else:
				matrix[y][x] = " "
		
		# if is_box
		elif matrix[y][x-1] == "$":
			print "Box Found"
			if matrix[y][x-2] == " ":
				matrix[y][x-2] = "$"
				matrix[y][x-1] = "@"
				if target_found == True:
					matrix[y][x] = "."
					target_found = False
				else:
					matrix[y][x] = " "
			elif matrix[y][x-2] == ".":
				matrix[y][x-2] = "*"
				matrix[y][x-1] = "@"
				if target_found == True:
					matrix[y][x] = "."
					target_found = False
				else:
					matrix[y][x] = " "
				
				
		# if is_box_on_target
		elif matrix[y][x-1] == "*":
			print "Box on target Found"
			if matrix[y][x-2] == " ":
				matrix[y][x-2] = "$"
				matrix[y][x-1] = "@"
				if target_found == True:
					matrix[y][x] = "."
				else:
					matrix[y][x] = " "
				target_found = True
				
			elif matrix[y][x-2] == ".":
				matrix[y][x-2] = "*"
				matrix[y][x-1] = "@"
				if target_found == True:
					matrix[y][x] = "."
				else:
					matrix[y][x] = " "
				target_found = True
				
		# if is_target
		elif matrix[y][x-1] == ".":
			print "Target Found"
			matrix[y][x-1] = "@"
			if target_found == True:
				matrix[y][x] = "."
			else:
				matrix[y][x] = " "
			target_found = True
		
		# else
		else:
			print "There is a wall here"
	
	elif direction == "R":
		print "######### Moving Right #########"

		# if is_space
		if matrix[y][x+1] == " ":
			print "OK Space Found"
			matrix[y][x+1] = "@"
			if target_found == True:
				matrix[y][x] = "."
				target_found = False
			else:
				matrix[y][x] = " "
		
		# if is_box
		elif matrix[y][x+1] == "$":
			print "Box Found"
			if matrix[y][x+2] == " ":
				matrix[y][x+2] = "$"
				matrix[y][x+1] = "@"
				if target_found == True:
					matrix[y][x] = "."
					target_found = False
				else:
					matrix[y][x] = " "
			
			elif matrix[y][x+2] == ".":
				matrix[y][x+2] = "*"
				matrix[y][x+1] = "@"
				if target_found == True:
					matrix[y][x] = "."
					target_found = False
				else:
					matrix[y][x] = " "				
		
		# if is_box_on_target
		elif matrix[y][x+1] == "*":
			print "Box on target Found"
			if matrix[y][x+2] == " ":
				matrix[y][x+2] = "$"
				matrix[y][x+1] = "@"
				if target_found == True:
					matrix[y][x] = "."
				else:
					matrix[y][x] = " "
				target_found = True
				
			elif matrix[y][x+2] == ".":
				matrix[y][x+2] = "*"
				matrix[y][x+1] = "@"
				if target_found == True:
					matrix[y][x] = "."
				else:
					matrix[y][x] = " "
				target_found = True
			
		# if is_target
		elif matrix[y][x+1] == ".":
			print "Target Found"
			matrix[y][x+1] = "@"
			if target_found == True:
				matrix[y][x] = "."
			else:
				matrix[y][x] = " "
			target_found = True
			
		# else
		else:
			print "There is a wall here"		

	elif direction == "D":
		print "######### Moving Down #########"

		# if is_space
		if matrix[y+1][x] == " ":
			print "OK Space Found"
			matrix[y+1][x] = "@"
			if target_found == True:
				matrix[y][x] = "."
				target_found = False
			else:
				matrix[y][x] = " "
		
		# if is_box
		elif matrix[y+1][x] == "$":
			print "Box Found"
			if matrix[y+2][x] == " ":
				matrix[y+2][x] = "$"
				matrix[y+1][x] = "@"
				if target_found == True:
					matrix[y][x] = "."
					target_found = False
				else:
					matrix[y][x] = " "
			
			elif matrix[y+2][x] == ".":
				matrix[y+2][x] = "*"
				matrix[y+1][x] = "@"
				if target_found == True:
					matrix[y][x] = "."
					target_found = False
				else:
					matrix[y][x] = " "
		
		# if is_box_on_target
		elif matrix[y+1][x] == "*":
			print "Box on target Found"
			if matrix[y+2][x] == " ":
				matrix[y+2][x] = "$"
				matrix[y+1][x] = "@"
				if target_found == True:
					matrix[y][x] = "."
				else:
					matrix[y][x] = " "
				target_found = True
				
			elif matrix[y+2][x] == ".":
				matrix[y+2][x] = "*"
				matrix[y+1][x] = "@"
				if target_found == True:
					matrix[y][x] = "."
				else:
					matrix[y][x] = " "
				target_found = True
		
		# if is_target
		elif matrix[y+1][x] == ".":
			print "Target Found"
			matrix[y+1][x] = "@"
			if target_found == True:
				matrix[y][x] = "."
			else:
				matrix[y][x] = " "
			target_found = True
			
		# else
		else:
			print "There is a wall here"

	elif direction == "U":
		print "######### Moving Up #########"

		# if is_space
		if matrix[y-1][x] == " ":
			print "OK Space Found"
			matrix[y-1][x] = "@"
			if target_found == True:
				matrix[y][x] = "."
				target_found = False
			else:
				matrix[y][x] = " "
		
		# if is_box
		elif matrix[y-1][x] == "$":
			print "Box Found"
			if matrix[y-2][x] == " ":
				matrix[y-2][x] = "$"
				matrix[y-1][x] = "@"
				if target_found == True:
					matrix[y][x] = "."
					target_found = False
				else:
					matrix[y][x] = " "

			elif matrix[y-2][x] == ".":
				matrix[y-2][x] = "*"
				matrix[y-1][x] = "@"
				if target_found == True:
					matrix[y][x] = "."
					target_found = False
				else:
					matrix[y][x] = " "					
					
		# if is_box_on_target
		elif matrix[y-1][x] == "*":
			print "Box on target Found"
			if matrix[y-2][x] == " ":
				matrix[y-2][x] = "$"
				matrix[y-1][x] = "@"
				if target_found == True:
					matrix[y][x] = "."
				else:
					matrix[y][x] = " "
				target_found = True
				
			elif matrix[y-2][x] == ".":
				matrix[y-2][x] = "*"
				matrix[y-1][x] = "@"
				if target_found == True:
					matrix[y][x] = "."
				else:
					matrix[y][x] = " "
				target_found = True
					
		# if is_target
		elif matrix[y-1][x] == ".":
			print "Target Found"
			matrix[y-1][x] = "@"
			if target_found == True:
				matrix[y][x] = "."
			else:
				matrix[y][x] = " "
			target_found = True
			
		# else
		else:
			print "There is a wall here"
	
	drawLevel(matrix)
	
	print "Boxes remaining: " + str(len(myLevel.getBoxes()))
	
	if len(myLevel.getBoxes()) == 0:
		myEnvironment.screen.fill((0, 0, 0))
		print "Level Completed"
		global current_level
		current_level += 1
		initLevel(level_set,current_level)	
		
def initLevel(level_set,level):
	# Create an instance of this Level
	global myLevel
	myLevel = Level(level_set,level)

	# Draw this level
	drawLevel(myLevel.getMatrix())
	
	global target_found
	target_found = False
	

# Create the environment
myEnvironment = Environment()

# Choose a theme
theme = "default"

# Choose a level set
level_set = "original"

# Set the start Level
current_level = 1

# Initialize Level
initLevel(level_set,current_level)

target_found = False

while True:
	
	for event in pygame.event.get():
		if event.type == pygame.KEYDOWN:
			if event.key == pygame.K_LEFT:
				movePlayer("L",myLevel)
			elif event.key == pygame.K_RIGHT:
				movePlayer("R",myLevel)
			elif event.key == pygame.K_DOWN:
				movePlayer("D",myLevel)
			elif event.key == pygame.K_UP:
				movePlayer("U",myLevel)
			elif event.key == pygame.K_u:
				drawLevel(myLevel.getLastMatrix())
			elif event.key == pygame.K_r:
				initLevel(level_set,current_level)
			elif event.key == pygame.K_ESCAPE:
				pygame.quit()
				sys.exit()
		elif event.type == pygame.QUIT:
			pygame.quit()
			sys.exit()