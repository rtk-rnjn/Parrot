from utilities.regex import TIME_REGEX
from discord.ext.commands import clean_content
from utilities import exceptions as ex
def convert_time(arguments:str):
		try: 
			total_sec = int(arguments)
			return total_sec
		except ValueError:
			pass
		time_array = TIME_REGEX.findall(arguments)
		total_sec = 0
		for segment in time_array:
				number = int(segment[0])
				multiplier = str(segment[1]).lower()
				if multiplier == 's': total_sec += 1 * number
				if multiplier == 'm': total_sec += 60 * number
				if multiplier == 'h': total_sec += 60 * 60 * number
				if multiplier == 'd': total_sec += 24 * 60 * 60 * number
		else:
			 raise ex.TimeError()
		return total_sec


def conver_bool(text):
		if text.lower() in ('yes', 'y', 'true', 't', '1', 'enable', 'on', 'o'):
				return True
		elif text.lower() in ('no', 'n', 'false', 'f', '0', 'disable', 'off', 'x'):
				return False


def reason_convert(text:clean_content):
		return text[:450:]