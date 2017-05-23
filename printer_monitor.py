from datetime import timedelta
from netsnmp import snmpget, Varbind
from os import environ, path
from re import findall, search
from subprocess import PIPE, Popen
from sys import argv, exit
import time

usage = 'Usage: python %s <printer_address>...' % argv[0]

mibs_dir = path.abspath(path.join(path.dirname( __file__ ), '..', 'mibs'))
mibs_to_load = mibs_dir + '/Printer-MIB.my:' + mibs_dir + '/DISMAN-EVENT-MIB.txt' #colon-separated (!) list
environ['MIBS'] = mibs_to_load

ignore_list = 'low:|lite:|no paper|tomt for papir|low power mode|energy saver mode|energisparemodus|modus for lavt str|warming up|warmer opp'

def run_script(script, stdin=None):
    '''Returns (stdout, stderr); raises error on non-zero return code'''
    proc = Popen(['bash', '-c', script], stdout=PIPE, stderr=PIPE, stdin=PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode:
        raise ScriptException(proc.returncode, stdout, stderr)
    return stdout, stderr

class ScriptException(Exception):
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

def get_by_mib(device_address, mib):
    '''Returns the value of a given Management Information Base (MIB) for a network device'''
    return snmpget(Varbind(mib), DestHost = device_address, Community = 'public', Version = 1)

def get_error_list(printer_address):
    '''Returns all errors from a printer'''
    script = 'snmpwalk -v 2c -c public -M %s/ -m all %s | grep -E Printer-MIB::prtAlertDescription.' % (mibs_dir, printer_address)
    try:
        script_result = run_script(script)
    except ScriptException as e:
        if len(e.stderr) is 0:
            return None
        elif 'snmpwalk: Unknown host' in e.stderr:
            return '[%s] host \'%s\' unknown or offline' % (printer_address.split('.')[0], printer_address)
        else:
            return '[%s] unexpected error: \'%s\'' % (printer_address.split('.')[0], e.stderr)
    return parse_errors(printer_address, list(filter(None, run_script(script)[0].split('\n'))), ignore_list)

def parse_errors(printer_address, error_list, ignore_list):
    '''Generates a ready-to-print string of a printer's errors'''
    parsed_errors = ''
    for error in error_list:
        err_id = findall(r'\.(\d+\.\d+)', error)[0]
        try:
            err_desc = findall(r'"(.*?)\s\{', error)[0]
        except IndexError:
            err_desc = get_by_mib(printer_address, 'prtAlertDescription.' + err_id)[0].split(' {')[0]
        if not search(ignore_list, err_desc.lower()):
            err_ticks = int(get_by_mib(printer_address, 'prtAlertTime.' + err_id)[0])
            system_uptime_ticks = int(get_by_mib(printer_address, 'sysUpTimeInstance')[0])
            err_time = str(timedelta(seconds=(system_uptime_ticks - err_ticks)/100)) #error time appears relative to system uptime
            parsed_errors += '[%s] \'%s\' in %s\n' % (printer_address.split('.')[0], err_desc, err_time)
    return parsed_errors

if __name__ == '__main__':
    if len(argv) > 1:
        start_time = time.time()
        parsed_errors = ''
        for arg in argv[1:]:
            errors = get_error_list(arg)
            if errors:
                parsed_errors += errors
        end_time = time.time()
        if len(parsed_errors) > 0:
            print parsed_errors
            print '\nDONE: %i printers checked in %.1f seconds' % (len(argv)-1, end_time - start_time)
    else:
        print usage; exit(1)
