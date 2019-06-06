import glob, os
import time
import random
import sys
from StcPython import StcPython

############# AUTOMATED TESTS LOOP ################
############# Loop L2 mixed test  #################
###################################################

# NOTE: test in xml is configured as follows:
#	Port 1/1 IP - 192.168.0.100
#	Port 1/2 IP - 192.168.0.104
#	Default gateway (both ports) - 192.168.0.102
#	Chassis IP 		 - 10.2.100.6

#	Target must have configured MTU 9000.
#	Example configuration:
#	ifconfig bnxt2 up;
#	ifconfig bnxt3 up;
#	ifconfig bridge create;
#	ifconfig bridge0 addm bnxt2 addm bnxt3 ;
#	ifconfig bridge0 promisc up;
#	ifconfig bridge0 192.168.0.102;
#	ifconfig bnxt2 mtu 9000;
#	ifconfig bnxt3 mtu 9000;
#	ifconfig bridge0 mtu 9000


# Create Spirent API instance
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


# Attach chassis ports and apply configuration
def attach_and_apply():
# Connect to chassis and try to reserve and map the ports. Set RevokeOwner to TRUE to
# kick out the other user (takes a minute)
	rv = stc.perform('attachPorts', RevokeOwner='FALSE')
	if not rv:
		print("Error: Failed to reserve ports - exiting..\n")
		exit(1)

# Apply configuration (verify and upload to chassis)
	stc.apply()

def run_test(file_name):
	common_init(file_name)
	attach_and_apply()

	print("Starting sequencer for test " + file_name + "\n")
	stc.perform('sequencerStart')

	rv = stc.waitUntilComplete() #blocking
	stc.perform('devicesStopAll')
	print("Sequencer stopped with result: %s\n" % rv)
	return rv
		

############################################# MAIN LOOP ######################################

testfile = "brcm-l2-with-linkfail-with-verify.xml"
print("RUNNING TEST %s\n\n" % testfile)
rv = run_test(testfile)
if rv == 'FAILED':
	sys.exit(-1)
