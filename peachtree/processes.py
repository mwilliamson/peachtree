import os
import collections
import tempfile
import errno
import json

import spur
import psutil


local_shell = spur.LocalShell()


def start(commands):
    run_dir = tempfile.mkdtemp(prefix="process-set-")
    
    with open(os.path.join(run_dir, "names"), "w") as names_file:
        json.dump(commands.keys(), names_file)
    
    def start_process((name, command_args)):
        output_file = os.path.join(run_dir, "{0}.output".format(name))
        command = " ".join(map(_escape_sh, command_args))
        redirected_command = ["sh", "-c", "{0} > {1} 2>&1".format(command, output_file)]
        process = local_shell.spawn(redirected_command, store_pid=True)
        process_info = _process_info_for_pid(process.pid)
        with open(os.path.join(run_dir, "{0}.process-info".format(name)), "w") as process_info_file:
            json.dump({"pid": process_info.pid, "startTime": process_info.start_time}, process_info_file)
        return (name, process_info)
    
    return ProcessSet(run_dir, dict(map(start_process, commands.iteritems())))


def from_dir(run_dir):
    with open(os.path.join(run_dir, "names")) as names_file:
        names = json.load(names_file)
        
    def load_process_info(name):
        with open(os.path.join(run_dir, "{0}.process-info".format(name))) as process_info_file:
            properties = json.load(process_info_file)
            return ProcessInfo(properties["pid"], properties["startTime"])
        
    process_infos = map(load_process_info, names)
        
    return ProcessSet(run_dir, dict(zip(names, process_infos)))


ProcessInfo = collections.namedtuple("ProcessInfo", ["pid", "start_time"])
    
    
class ProcessSet(object):
    def __init__(self, run_dir, processes):
        self.run_dir = run_dir
        self._processes = processes

    def all_running(self):
        return all(self._is_running_each_process())
    
    def any_running(self):
        return any(self._is_running_each_process())
    
    def all_output(self):
        names = sorted(self._processes.keys())
        return "".join(
            "{0}:\n{1}".format(name, _indent(self._output(name)))
            for name in names
        )
        
    def kill_all(self):
        for process_info in self._processes.itervalues():
            _kill(process_info)
            
    
    def _is_running_each_process(self):
        return map(_process_is_running, self._processes.itervalues())
    
    def _output(self, name):
        # TODO: remove duplication
        output_file = os.path.join(self.run_dir, "{0}.output".format(name))
        try:
            with open(output_file) as output:
                return output.read()
        except IOError as error:
            if error.errno == errno.ENOENT:
                return ""
            else:
                raise


def _indent(string):
    def indent_line(line):
        if line:
            return "    {0}\n".format(line)
        else:
            return line
        
    lines = string.split("\n")
    indented_lines = map(indent_line, lines)
    return "".join(indented_lines)


def _process_is_running(process_info):
    try:
        process = psutil.Process(process_info.pid)
    except psutil.NoSuchProcess:
        return False
    if process.status in [psutil.STATUS_DEAD, psutil.STATUS_ZOMBIE]:
        return False
    return _process_info_for_pid(process_info.pid) == process_info


def _kill(process_info):
    if _process_is_running(process_info):
        local_shell.run(["kill", str(process_info.pid)])

def _process_info_for_pid(pid):
    start_time = _process_start_time_from_pid(pid)
    return ProcessInfo(pid, start_time)
    

def _process_start_time_from_pid(pid):
    return psutil.Process(pid).create_time
    
    
def _escape_sh(value):
    return "'" + value.replace("'", "'\\''") + "'"
