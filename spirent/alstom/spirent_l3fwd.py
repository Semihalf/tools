import glob, os
import time
import random
import sys
from StcPython import StcPython

################### Spirent L3 forward test ####################
# - Loads XML configuration passed in argument
# 	(NOTE: assumes two ports used)
# - Starts traffic generators
# - Prints generator framerate
# - Prints RX framerates on both ports every 1s over 10s period
# - Saves results in CSV files
###############################################################

# Example configuration in XML:
#	Port 1/3 IP - 192.168.202.100
#	Port 1/4 IP - 192.168.203.100
#	Default gateway (Port 1/3) - 192.168.202.2
#	Default gateway (Port 1/4) - 192.168.203.2
#	Chassis IP  - 10.2.100.6 (fixed)

# Set KICK_OTHER_USERS to TRUE to kick out the other user connected to Spirent (takes a minute)
KICK_OTHER_USERS = 'FALSE'

# Run traffic generators for this many seconds
RUN_LENGTH = 10

# Create Spirent API instance
print("Initializing STC..")
stc = StcPython()

# Common setup before test
def common_init(file_name):
# Create project - the root object
	hProject = stc.create("project")

# Print WARN and ERROR messages
	stc.config("automationoptions", logTo='stdout', logLevel='WARN')

# Load configuration from XML, set results dir, set sequencer to stop on error
	stc.perform('loadfromxml', filename=file_name)
	results_dir = os.path.basename(os.path.splitext(testfile)[0])
	stc.config(hProject + '.testResultSetting', saveResultsRelativeTo='NONE', resultsDirectory=results_dir)
	stc.config('system1.sequencer', errorHandler='STOP_ON_ERROR')

# Subscribe to test results. Configured attributes will be saved to .csv results file every 1 second of
# the test. Possible fields in viewAttributeList are listed in API docs: 'RxStreamSummaryResults.htm'.
# Results may be viewed in .csv file or you may browse the SQL .db file directly.
# Best way to view them is via Results API object.
	rx_dataset = stc.subscribe(parent=hProject, resultParent=hProject, configType='StreamBlock', resultType='RxStreamSummaryResults', viewAttributeList='framerate' , interval='1', filenamePrefix='RxStreamSummaryResults')

# Subscribe to generator and analyzer results
	generator_dataset = stc.subscribe(parent=hProject, resultParent=hProject, configType='generator', resultType='generatorportresults', filterList='', viewAttributeList='totalframecount generatorframecount totalframerate generatorframerate totalbitrate generatorbitrate', interval='1', filenamePrefix='generatorportresults')
	analyzer_dataset = stc.subscribe(parent=hProject, resultParent=hProject, configType='analyzer', resultType='analyzerportresults', filterList='',
	viewAttributeList='totalframecount totalframerate totalbitrate', interval='1', filenamePrefix='analyzerportresults')

# Search for objects of type 'Port' in the configuration and extract them
	rv = stc.perform('GetObjects', ClassName='Port', Condition='IsVirtual=false')
	ports = str.split(rv['ObjectList'])
	if len(ports) != 2:
		print("Error: failed to find two ports in configuration")
		exit(1)

	return ports


# Attach chassis ports and apply configuration
def attach_and_apply():
# Connect to chassis and try to reserve and map the ports. 
	print("Attaching ports..")
	rv = stc.perform('attachPorts', RevokeOwner=KICK_OTHER_USERS)
	if not rv:
		print("Error: Failed to reserve ports - exiting..")
		exit(1)

# Apply configuration (verify and upload to chassis)
	stc.apply()

def get_rx_framerates(ports):
	# Check RX frames per second on both ports
	sb1 = stc.get(ports[0], 'children-StreamBlock')
	rx_results1 = stc.get(sb1, 'children-RxStreamSummaryResults')
	framerate1 = stc.get(rx_results1, 'FrameRate')
	sb2 = stc.get(ports[1], 'children-StreamBlock')
	rx_results2 = stc.get(sb2, 'children-RxStreamSummaryResults')
	framerate2 = stc.get(rx_results2, 'FrameRate')

	return framerate1, framerate2

def get_generator_framerates(ports):
	# Check TX (generator) frames per second on both ports
	generator1 = stc.get(ports[0], 'children-Generator')
	generator2 = stc.get(ports[1], 'children-Generator')
	generator_results1 = stc.get(generator1, 'children-GeneratorPortResults')
	generator_results2 = stc.get(generator2, 'children-GeneratorPortResults')
	generator_framerate1 = stc.get(generator_results1, 'GeneratorFrameRate')
	generator_framerate2 = stc.get(generator_results2, 'GeneratorFrameRate')

	return generator_framerate1, generator_framerate2
	
def run_test(file_name):
	ports = common_init(file_name)
	attach_and_apply()

	# Start generators without using sequencer
	print("Starting traffic generators")
	generator1 = stc.get(ports[0], 'children-Generator')
	generator2 = stc.get(ports[1], 'children-Generator')
	stc.perform('GeneratorStart', GeneratorList=generator1)
	stc.perform('GeneratorStart', GeneratorList=generator2)

	time.sleep(1)
	prev_gen1, prev_gen2 = -1,-1
	for x in xrange(RUN_LENGTH):
		gen1, gen2 = get_generator_framerates(ports)
		f1, f2 = get_rx_framerates(ports)
		if gen1 != prev_gen1 or gen2 != prev_gen2:
			print("Generator at Port1 framerate: " + gen1 + "pps, Generator at Port2 framerate: " + gen2 + "pps")
		print("Port1 RX framerate: " + f1 + "pps, Port2 RX framerate: " + f2 + "pps")
		prev_gen1, prev_gen2 = gen1, gen2
		time.sleep(1)

	# Stop generators
	stc.perform('GeneratorStop', GeneratorList=generator1)
	stc.perform('GeneratorStop', GeneratorList=generator2)
	print("Generators stopped")

	# Disconnect from chassis, release ports and reset the config in chassis
	print("Disconnecting from chassis")
	stc.perform('chassisDisconnectAll')

	rv = 0
	return rv
		

############################################# MAIN LOOP ######################################

if len(sys.argv) < 2:
	print("Pass Spirent test configuration XML as argument")
	sys.exit(-1)

testfile = sys.argv[1]
print("RUNNING TEST %s" % testfile)
rv = run_test(testfile)
if rv == 'FAILED':
	sys.exit(-1)
