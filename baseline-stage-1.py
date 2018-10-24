import numpy as np
import sys
import re

# For the purposes of this script we are assuming 196 narrow beams (n_i (= 14) x n_j (= 14)), each with up to 40 channels (n_chan). Also by always selecting the lowest channel number, the frequency reuse is maximised

def import_data(data = np.array([]), data_file = None, n_i = 14, n_j = 14, channels=40):
	"""
	   Reads raw data/data files into an array (channel list) of slices of the beam formation in each channel. 
	   Also outputs an allocated carriers dictionary, which gives a string describing the carrier's beam location, channel and unique code, along with its priority.

	   Parameters
	   ----------
	   data : np.array/list, the raw data, each carrier is referenced by a 5-element dict: keys=['i', 'j', 'channel', 'priority', 'unique_code']. priorities currently set = 0
	   data_file : str, the location of the raw data's file (currently not functioning as formatting is as of yet undecided)

	   returns
	   -------
	   channel_list : np.array[18,22,40], 18x18 are n_i and n_j, 40 is the number of channels, unallocated channels are stored as 0, allocated channels are assigned a carrier code, which is used in a dictionary of allocated carriers, the values are the carrier's unique_code
	   allocated_carriers : dict, keys are the carrier codes (='i:j:channel:u_code'), their value is the priority of the carrier
	"""

	if not data_file == None: pass # will open data file using a to-be-defined function: data = open_carrier_data_file(), will also define save_carrier_data_file()

	elif type(data) == list or type(data) == np.ndarray: pass # replace with function to check data is of the correct format, else raises an error.

	else:  raise TypeError("Please input either raw data or a path to the data files (using parameters data, or data_file") # raises an error if no data is defined at all.


	channel_list, allocated_carriers = convert_from_raw(data, n_i, n_j, channels)


	return channel_list, allocated_carriers

def process_new_carrier(carrier_info):
	"""
	   Interprets new carrier information, currently this will just spit out unzipped data, however it will be used for carefully assigning priority scores.


	   Iterate over new carriers for each carrier that needs to be defined, sort by priority so that highest priorities are assigned first.
	
	   Parameters
	   ----------
	   carrier_info : dict, this contains dict containing the carrier location (beam/cluster), user priority/package, it will contain the bandwidth request

	   Returns
	   -------
	   i : int, the x-location of the beam in which to assign carrier
	   j : int, the y-location of the beam in which to assign carrier
	   priority : float, the UT's priority score
	   unique_code : str, UT identification
	"""

	i, j = carrier_info['i'], carrier_info['j']
	priority = float(carrier_info['priority'])
	ucode = carrier_info['ucode']

	return i, j, priority, ucode

def scan_carriers(centre_i, centre_j, channel_list, priority=0, possible_channels=np.arange(40)):
	"""
	   Scans the surrounding coordinates of the target beam for any available/unused channels in the 19-beam region.

	   Parameters
	   ----------
	   centre_i : int, x-coordinate for the target beam location
	   centre_j : int, y-coordinate for the target beam location
	   channel_list : 3d array of pre-allocated channels.
	   priority : float, the priority score for the channel (if 0 then unallocated in the 19-beam region, 18 then the maximum if it's allocated in all other beams, and 100 added if the channel is already allocated in that beam)

	   Returns
	   -------
	   good_channels : list, all channels below the priority score (if priority is 0, then this is all currently unallocated channels)
	   imperfect_channels : np.array, score for each channel, 0 is unallocated in the 19-beam region, 18 is the theoretical maximum if channel is assigned in every beam
	"""

	imperfect_channels = np.zeros(len(channel_list[0][0]))

	neighbour_coords = create_neighbour_coords(centre_i, centre_j) # neighbour_coords is now given an array of all coordinates for the 18 beam region surrounding the centre beam

	good_channels = []

	for channel in possible_channels:

		if channel_list[centre_i][centre_j][channel] != 0: # i.e. if channel is already assigned

			imperfect_channels[channel] = 100


		for i,j in neighbour_coords:

			if channel_list[i][j][channel] != 0:

				imperfect_channels[channel] += 1

		if imperfect_channels[channel] <= priority: # this will later be used as a priority box, enabling imperfect channels to pass as good channels; the appropriate channels can be reallocated to suit.
			
			good_channels.append(channel)



	return good_channels, imperfect_channels

def create_neighbour_coords(c_i, c_j):
	"""
	   Finds the coordinates for all non-centre beams in the 19-beam region

	   Parameters
	   ----------
	   c_i : int, central x-coordinate of the 19-beam region
	   c_i : int, central y-coordinate of the 19-beam region

	   Returns
	   -------
	   coords : np.array, coordinates of all 18 beams in region
	"""

	coords = []

	for i in [c_i-1, c_i+1]:

		for j in [c_j-1, c_j+1, c_j-3, c_j+3]:

			coords.append([i,j])

			#print(i,j)

	for j in [c_j-2, c_j+2, c_j-4, c_j+4]:

		coords.append([c_i,j])

		#print(c_i, j)

	for i in [c_i-2, c_i+2]:

		for j in [c_j-1, c_j, c_j+1]:

			coords.append([i,j])

	return np.array(coords)

def randomly_generate_carriers(n_i, n_j, channels, carrier_quantity=1000, return_format = 'read'): # Add a feature to return a carrier list in raw format, current issue with it allocating adjacent carriers
	"""
	   Randomly allocates carriers to each beam

	   n_i : int, x-dimension for number of beams on axis
	   n_j : int, y-dimension for number of beams on axis
	   random_weight : float (0 to 1), random portion of beams to assign channels to. Default = 0.6

	   Returns
	   -------
	   channel_list : np.array (3D), containing list of channels in appropriate format.
	   allocated_carriers : dict, all allocated carriers keys defined by location, channel and ucode

	   raw_carriers : np.array, all allocated carriers, each defined by a dict containing their coordinates, channel, ucode and priority
	"""

	channel_list = np.zeros(shape = [n_i + 4, n_j + 8, 40])

	carriers = np.arange( (n_i + 4) * (n_j + 8) * 40)

	allocated_carriers = {}

	for carrier in range(carrier_quantity):

		new_carrier = generate_random_carrier(n_i, n_j, allocated_carriers)

		channel_list, allocated_carriers = base_carrier_manager([new_carrier], n_i, n_j, channels, convert_to_raw(channel_list, allocated_carriers))[0:2]


	if return_format == 'read'  : 

		return channel_list, allocated_carriers

	elif return_format == 'raw' :

		raw_carriers = convert_to_raw(channel_list, allocated_carriers)

		return raw_carriers

def generate_random_carrier(n_i, n_j, allocated_carriers):
	"""
	   Generates a randomly located and priority carrier in the allocated carrier's array, with its own unique code
	"""

	c_i = np.random.randint(2, n_i+2)
	c_j = np.random.randint(4, n_j+4)

	active_ucodes = []

	for carrier in allocated_carriers.keys():
		active_ucodes.append(int((re.split(':', carrier))[3]))

	# active_ucodes.sort(); kind of pointless, but ordering is optional

	carriers = np.arange( (n_i + 4) * (n_j + 8) * 40)

	carriers = np.delete(carriers, active_ucodes)

	ucode_element = np.random.randint(len(carriers))

	ucode = str(carriers[ucode_element])

	priority = np.random.randint(10)

	new_carrier = {'i':c_i, 'j':c_j, 'priority':priority, 'ucode':ucode}

	return new_carrier

def convert_to_raw(channel_list, allocated_carriers):
	"""
	   Reads the channel_list and allocated_carriers and returns a raw list of dictionary stored data


	"""

	raw_carriers = []
		
	for carrier_code in allocated_carriers.keys():

		i, j, channel, ucode = re.split(':', carrier_code)
		priority = allocated_carriers[carrier_code]

		raw_carriers.append({'i':int(i), 'j':int(j), 'channel':int(channel), 'ucode':ucode, 'priority':float(priority)})

	return np.array(raw_carriers)

def convert_from_raw(raw_data, n_i=14, n_j=14, channels=40):
	"""
	   Reads raw data in, along with the beam formation data, and returns the data in a more readable format, ready for operating on
	"""

	channel_list = np.zeros(shape = [n_i + 4, n_j + 8, channels]) # initiates an empty array for channel-sliced beam formations

	allocated_carriers = {} # initiates a dictionary for uniquely identified carriers

	for c_data in raw_data: # loops over each file in raw_data  

		i, j, channel = c_data['i'], c_data['j'], c_data['channel']
		priority = float(c_data['priority'])
		u_code = c_data['ucode']

		carrier_code = '{i}:{j}:{channel}:{u_code}'.format(i=i, j=j, channel=channel, u_code=u_code) #nifty

		allocated_carriers[carrier_code] = priority

		channel_list[int(i)][int(j)][int(channel)] = u_code

	return channel_list, allocated_carriers

def select_random_carrier(allocated_carriers):

	key_list = list(allocated_carriers.keys())

	random_key = np.random.randint(len(key_list))

	return key_list[random_key]

def deallocate_carrier(carrier_code, channel_list, allocated_carriers):

	while True:
		try:

			i, j, channel, ucode = re.split(':', carrier_code)

			priority = allocated_carriers[carrier_code]

			del allocated_carriers[carrier_code]
			channel_list[int(i)][int(j)][int(channel)] = 0

			break

		except: 

			assign_carrier(channel_list, allocated_carriers, i, j, channel, ucode, priority)

			print('carrier deallocation failed')

			return channel_list, allocated_carriers

	return channel_list, allocated_carriers


def reallocate_carrier():

	deallocate_carrier()

	allocate_carriers()


def assign_carrier(channel_list, allocated_carriers, c_i, c_j, channel, ucode, priority = 0):
	"""
	   Adds the carrier/channel to the array of channels and the list of allocated carriers

	   Parameters
	   ----------
	   channel_list : np.array (3d), for beam formation and channel
	   allocated_carriers : dict, list of all the carriers allocated, values are the priority, keys are the carrier codes (='i:j:channel:u_code')
	   c_i : int, x-coordinate of the target beam
	   c_j : int, y-coordinate of the target beam
	   channel : int, channel of the available channel
	   u_code : unique code of the carrier
	   priority : float, some number which describes the priority of the UT

	   Returns
	   -------
	   channel_list : np.array (3d), updated channel_list for new carrier
	   allocated_carriers : dict, updated allocated_carriers for new carrier
	"""

	channel_list[c_i][c_j][channel] = ucode

	carrier_code = '{i}:{j}:{channel}:{u_code}'.format(i=c_i, j=c_j, channel=channel, u_code=ucode)

	allocated_carriers[carrier_code] = priority

	return channel_list, allocated_carriers


def check_for_competition(new_carrier_list):
	"""
	   Checks all carrier candidates for any conflicts; i.e. where two proposed channels for two different carriers are the same, and chooses which UT gets priority.
	"""
	
	for each_carrier in new_carrier_list:

		good_channels = each_carrier['good_channels']

	for ut in range(len(new_carrier_list)):

		for other_ut in np.delete(range(len(new_carrier_list)), ut):

			for channel in good_channels[ut]:

				for other_channel in good_channels[other_ut]:

					if channel == other_channel:

						if create_neighbour_coords(each_carrier[c_i], each_carrier[c_j]):

							pass# finish writing this, scans list to see if coords of one are within region of the other

	return competing_u_codes


def base_carrier_manager(new_carrier_list, n_i = 14, n_j = 14, channels = 40, data = np.array([]), data_file = None, return_format = 'read'):
	"""
	   Runs the carrier manager algorithm

	   Parameters
	   ----------
	   new_carrier_list : list of carriers to be assigned, contains 4-element dicts [i, j, priority?, ucode]
	   data : np.array/list, the raw data, each carrier is referenced by a 5-element dict: [i, j, channel, priority?, unique_code]. priorities currently set = 0
	   data_file : str, the location of the raw data's file (currently not functioning as formatting is as of yet undecided)

	   Returns
	   -------
	   data/data_file : updated data/data_file with updated carriers
	"""

	if len(data) > 0 or data_file != None: 
		channel_list, allocated_carriers = import_data(data, data_file, n_i, n_j, channels)

	else:
		allocated_carriers = {}
		channel_list = np.zeros(shape = [n_i + 4, n_j + 8, 40])

	for each_new_carrier in new_carrier_list:

		c_i, c_j, priority, u_code = process_new_carrier(each_new_carrier)

		good_channels, each_new_carrier['imperfect_channels'] = scan_carriers(c_i, c_j, channel_list, priority)

		while True:
			if len(good_channels) == 0:
				good_channels, each_new_carrier['imperfect_channels'] = scan_carriers(c_i, c_j, channel_list, priority)
				priority += 1

			else: 
				each_new_carrier['good_channels'] = good_channels
				each_new_carrier['final_priority'] = priority
				break

		channel_list, allocated_carriers = assign_carrier(channel_list, allocated_carriers, each_new_carrier['i'], each_new_carrier['j'],
			each_new_carrier['good_channels'][0], each_new_carrier['ucode'], each_new_carrier['priority'])


	"""
	#This stage is only required when carriers are assigned simultaniously, which they are currently not.
	for each_carrier in new_carrier_list:

		check_for_competition(new_carrier_list) #write a script to check there are no clashes between assigned carriers
	


	for each_carrier in new_carrier_list:
		channel_list, allocated_carriers = assign_carrier(channel_list, allocated_carriers, each_carrier['c_i'], each_carrier['c_j'],
			each_carrier['channel'], each_carrier['u_code'], each_carrier['priority'])

	"""


	if return_format == 'read':

		return channel_list, allocated_carriers, new_carrier_list

	elif return_format == 'raw':

		raw_carriers = convert_to_raw(channel_list, allocated_carriers)

		return raw_carriers

