import os
import platform
import pygame
import time

class Environment:

	# define some variables
	screen = None;
	size = None;

	
	def __init__(self):
	
		if platform.system() == "Windows":
			pygame.display.init()
			pygame.display.set_caption("pySokoban")
			self.size = (800,600)
			self.screen = pygame.display.set_mode(self.size)
		
		elif self.getUserInterface() == "graphics":
			pygame.display.init()
			pygame.display.set_caption("pySokoban")
			self.size = (800,600)
			self.screen = pygame.display.set_mode(self.size)
		else: 
			"Ininitializes a new pygame screen using the framebuffer"
			# Based on "Python GUI in Linux frame buffer"
			# http://www.karoltomala.com/blog/?p=679
			disp_no = os.getenv("DISPLAY")
			if disp_no:
				print "I'm running under X display = {0}".format(disp_no)
			
			# Check which frame buffer drivers are available
			# Start with fbcon since directfb hangs with composite output
			drivers = ['fbcon', 'directfb', 'svgalib']
			found = False
			for driver in drivers:
				# Make sure that SDL_VIDEODRIVER is set
				if not os.getenv('SDL_VIDEODRIVER'):
					os.putenv('SDL_VIDEODRIVER', driver)
				try:
					pygame.display.init()
				except pygame.error:
					print 'Driver: {0} failed.'.format(driver)
					continue
				found = True
				break
		
			if not found:
				raise Exception('No suitable video driver found!')
        
			self.size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
			print "Framebuffer size: %d x %d" % (self.size[0], self.size[1])
			self.screen = pygame.display.set_mode(self.size, pygame.FULLSCREEN)
		
		# Clear the screen to start
		self.screen.fill((0, 0, 0))        
		# Initialise font support
		pygame.font.init()
		# Disable mouse
		pygame.mouse.set_visible(False)
		# Render the screen
		pygame.display.update()

	def __del__(self):
		"Destructor to make sure pygame shuts down, etc."

	def getOS(self):
		return platform.system()

	def getUserInterface(self):
		if os.getenv("DISPLAY"):
			return "graphics"
		else:
			return "framebuffer"
		
	def getPath(self):
		return os.path.dirname(os.path.abspath(__file__))