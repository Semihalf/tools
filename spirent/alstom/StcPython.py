import os
import sys
import time
import atexit


class StcPython(object):

    def __init__(self):
        self.stcInt = None

        if sys.hexversion < 0x020605F0 or sys.hexversion >= 0x030500F0:
            raise ImportError('This version of StcPython requires Python '
                              'version 2.6.5 up to 3.4.4')

        # STC_PRIVATE_INSTALL_DIR may either be set as a system environment
        # variable or directly in the script.
        # Windows example:
        #   'C:/Program Files (x86)/Spirent Communications/Spirent TestCenter 4.40/Spirent TestCenter Application'
        # Linux example:
        #   /home/user/Spirent_TestCenter_4.40/Spirent_TestCenter_Application_Linux

        if 'STC_PRIVATE_INSTALL_DIR' not in os.environ:
            try:
		os.environ['STC_PRIVATE_INSTALL_DIR'] = '/home/mst/projects/anpa_nfp/spirent_cds/Spirent_TestCenter_4.78/Spirent_TestCenter_Application_Linux'
            except:
                raise Exception('Please replace STC_PRIVATE_INSTALL_DIR with '
                                'the actual STC install directory, or set the '
                                'system environment variable.')

        pvt_inst_dir = os.environ['STC_PRIVATE_INSTALL_DIR']
        if (not os.path.exists(pvt_inst_dir) or
            not os.path.exists(os.path.join(pvt_inst_dir, 'stcbll.ini'))):
            raise ValueError(pvt_inst_dir +
                             ' is not a valid STC install directory.')

        runningDir = os.getcwd()
        os.environ['STC_SCRIPT_RUNNING_DIR'] = runningDir
        os.chdir(pvt_inst_dir)
        sys.path.append(pvt_inst_dir)

        if sys.platform.startswith('linux'):
            install_exit_fix(self)

        if hex(sys.hexversion).startswith('0x2060'):
            self.stcInt = __import__('StcIntPython')
        elif hex(sys.hexversion).startswith('0x2070'):
            self.stcInt = __import__('StcIntPython27')
        else:
            self.stcInt = __import__('StcIntPython34')

        os.chdir(runningDir)

    def apply(self):
        return self.stcInt.salApply()

    def config(self, _object, **kwargs):
        svec = []
        StcPython._packKeyVal(svec, kwargs)
        return self.stcInt.salSet(_object, svec)

    def connect(self, *hosts):
        svec = StcPython._unpackArgs(*hosts)
        return self.stcInt.salConnect(svec)

    def create(self, _type, **kwargs):
        svec = []
        if _type.lower() != 'project':
            svec.append('-under')
            svec.append(kwargs.pop('under'))

        StcPython._packKeyVal(svec, kwargs)
        return self.stcInt.salCreate(_type, svec)

    def delete(self, handle):
        return self.stcInt.salDelete(handle)

    def disconnect(self, *hosts):
        svec = StcPython._unpackArgs(*hosts)
        return self.stcInt.salDisconnect(svec)

    def get(self, handle, *args):
        svec = StcPython._unpackArgs(*args)
        svecDashes = []
        for i, attName in enumerate(svec):
            svecDashes.append('-' + attName)
        retSvec = self.stcInt.salGet(handle, svecDashes)

        if len(retSvec) == 1:
            return retSvec[0]
        else:
            return StcPython._unpackGetResponseAndReturnKeyVal(retSvec, svec)

    def help(self, topic=''):
        if topic == '' or topic.find(' ') != -1:
            return 'Usage: \n' + \
                    '  stc.help(\'commands\')\n' + \
                    '  stc.help(<handle>)\n' + \
                    '  stc.help(<className>)\n' + \
                    '  stc.help(<subClassName>)'

        if topic == 'commands':
            allCommands = []
            for commandHelp in StcIntPythonHelp.HELP_INFO.values():
                allCommands.append(commandHelp['desc'])
            allCommands.sort()
            return '\n'.join(allCommands)

        info = StcIntPythonHelp.HELP_INFO.get(topic)
        if info:
            return 'Desc: ' + info['desc'] + '\n' + \
                   'Usage: ' + info['usage'] + '\n' + \
                   'Example: ' + info['example'] + '\n'

        return self.stcInt.salHelp(topic)

    def log(self, level, msg):
        return self.stcInt.salLog(level, msg)

    def perform(self, _cmd, **kwargs):
        svec = []
        StcPython._packKeyVal(svec, kwargs)
        retSvec = self.stcInt.salPerform(_cmd, svec)
        return StcPython._unpackPerformResponseAndReturnKeyVal(retSvec,
                                                               kwargs.keys())

    def release(self, *csps):
        svec = StcPython._unpackArgs(*csps)
        return self.stcInt.salRelease(svec)

    def reserve(self, *csps):
        svec = StcPython._unpackArgs(*csps)
        return self.stcInt.salReserve(svec)

    def sleep(self, seconds):
        time.sleep(seconds)

    def subscribe(self, **kwargs):
        svec = []
        StcPython._packKeyVal(svec, kwargs)
        return self.stcInt.salSubscribe(svec)

    def unsubscribe(self, rdsHandle):
        return self.stcInt.salUnsubscribe(rdsHandle)

    def waitUntilComplete(self, **kwargs):
        timeout = 0
        if 'timeout' in kwargs:
            timeout = int(kwargs['timeout'])

        sequencer = self.get('system1', 'children-sequencer')

        timer = 0

        while True:
            curTestState = self.get(sequencer, 'state')
            if 'PAUSE' in curTestState or 'IDLE' in curTestState:
                break

            time.sleep(1)
            timer += 1

            if timeout > 0 and timer > timeout:
                raise Exception('ERROR: Stc.waitUntilComplete timed out after '
                                '%s sec' % timeout)

        if ('STC_SESSION_SYNCFILES_ON_SEQ_COMPLETE' in os.environ and
            os.environ['STC_SESSION_SYNCFILES_ON_SEQ_COMPLETE'] == '1' and
            self.perform('CSGetBllInfo')['ConnectionType'] == 'SESSION'):
            self.perform('CSSynchronizeFiles')

        return self.get(sequencer, 'testState')

    @staticmethod
    def _unpackArgs(*args):
        svec = []
        for arg in args:
            if isinstance(arg, list):
                svec.extend(arg)
            else:
                svec.append(arg)
        return svec

    @staticmethod
    def _packKeyVal(svec, hash):
        for key, val in sorted(hash.items()):
            svec.append('-' + str(key))
            if isinstance(val, list):
                svec.append(' '.join(map(str, val)))
            else:
                svec.append(str(val))

    @staticmethod
    def _unpackGetResponseAndReturnKeyVal(svec, origKeys):
        useOrigKey = len(origKeys) == len(svec)/2
        hash = dict()
        for i in range(0, int(len(svec)/2)):
            key = svec[i*2]
            key = key[1:len(key)]
            val = svec[i*2+1]
            if useOrigKey:
                key = origKeys[i]
            hash[key] = val
        return hash

    @staticmethod
    def _unpackPerformResponseAndReturnKeyVal(svec, origKeys):
        origKeyHash = dict()
        for key in origKeys:
            origKeyHash[key.lower()] = key

        hash = dict()
        for i in range(0, int(len(svec)/2)):
            key = svec[i*2]
            key = key[1:len(key)]
            val = svec[i*2+1]
            if key.lower() in origKeyHash:
                key = origKeyHash[key.lower()]
            hash[key] = val
        return hash


_unhandled = None
_old_hook = None
_stc_inst = None


def _fix_exit():
    if _unhandled:
        # import traceback
        # traceback.print_exception(*_unhandled)
        _old_hook(*_unhandled)
        _stc_inst.stcInt.salShutdown(1)


def _save_uncaught_exception(ex, val, tb):
    global _unhandled
    _unhandled = (ex, val, tb)


def install_exit_fix(stc_inst):
    global _old_hook, _stc_inst
    _stc_inst = stc_inst
    sys.excepthook, _old_hook = _save_uncaught_exception, sys.excepthook
    atexit.register(_fix_exit)


def uninstall_exit_fix():
    global _old_hook, _unhandled, _stc_inst
    if _old_hook:
        sys.excepthook = _old_hook
        _old_hook = None
    _unhandled = None
    _stc_inst = None


# internal help info
class StcIntPythonHelp(object):

    def __init__(self):
        pass

    HELP_INFO = dict(
        create=dict(
            desc="create: -Creates an object in a test hierarchy",
            usage="stc.create( className, under = parentObjectHandle, propertyName1 = propertyValue1, ... )",
            example='stc.create( \'port\', under=\'project1\', location = "#{mychassis1}/1/2" )'),

        config=dict(
            desc="config: -Sets or modifies the value of an attribute",
            usage="stc.config( objectHandle, propertyName1 = propertyValue1, ... )",
            example="stc.config( stream1, enabled = true )"),

        get=dict(
            desc="get: -Retrieves the value of an attribute",
            usage="stc.get( objectHandle, propertyName1, propertyName2, ... )",
            example="stc.get( stream1, 'enabled', 'name' )"),

        perform=dict(
            desc="perform: -Invokes an operation",
            usage="stc.perform( commandName, propertyName1 = propertyValue1, ... )",
            example="stc.perform( 'createdevice', parentHandleList = 'project1' createCount = 4 )"),

        delete=dict(
            desc="delete: -Deletes an object in a test hierarchy",
            usage="stc.delete( objectHandle )",
            example="stc.delete( stream1 )"),

        connect=dict(
            desc="connect: -Establishes a connection with a Spirent TestCenter chassis",
            usage="stc.connect( hostnameOrIPaddress, ... )",
            example="stc.connect( mychassis1 )"),

        disconnect=dict(
            desc="disconnect: -Removes a connection with a Spirent TestCenter chassis",
            usage="stc.disconnect( hostnameOrIPaddress, ... )",
            example="stc.disconnect( mychassis1 )"),

        reserve=dict(
            desc="reserve: -Reserves a port group",
            usage="stc.reserve( CSP1, CSP2, ... )",
            example='stc.reserve( "//#{mychassis1}/1/1", "//#{mychassis1}/1/2" )'),

        release=dict(
            desc="release: -Releases a port group",
            usage="stc.release( CSP1, CSP2, ... )",
            example='stc.release( "//#{mychassis1}/1/1", "//#{mychassis1}/1/2" )'),

        apply=dict(
            desc="apply: -Applies a test configuration to the Spirent TestCenter firmware",
            usage="stc.apply()",
            example="stc.apply()"),

        log=dict(
            desc="log: -Writes a diagnostic message to the log file",
            usage="stc.log( logLevel, message )",
            example="stc.log( 'DEBUG', 'This is a debug message' )"),

        waitUntilComplete=dict(
            desc="waitUntilComplete: -Suspends your application until the test has finished",
            usage="stc.waitUntilComplete()",
            example="stc.waitUntilComplete()"),

        subscribe=dict(
            desc="subscribe: -Directs result output to a file or to standard output",
            usage="stc.subscribe( parent=parentHandle, resultParent=parentHandles, configType=configType, resultType=resultType, viewAttributeList=attributeList, interval=interval, fileNamePrefix=fileNamePrefix )",
            example="stc.subscribe( parent='project1', configType='Analyzer', resulttype='AnalyzerPortResults', filenameprefix='analyzer_port_counter' )"),

        unsubscribe=dict(
            desc="unsubscribe: -Removes a subscription",
            usage="stc.unsubscribe( resultDataSetHandle )",
            example="stc.unsubscribe( resultDataSet1 )"))
