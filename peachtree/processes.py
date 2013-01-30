import os
import tempfile
import errno
import json

import spur
import psutil

from . import dictobj


local_shell = spur.LocalShell()


def start(commands):
    run_dir = RunDirectory(tempfile.mkdtemp(prefix="process-set-"))
    process_set = ProcessSet(run_dir, {})
    process_set.start(commands)
    return process_set


def from_dir(run_dir):
    run_dir = RunDirectory(run_dir)
    names = run_dir.read_names()
    process_infos = map(run_dir.read_process_info, names)
        
    return ProcessSet(run_dir, dict(zip(names, process_infos)))


ProcessInfo = dictobj.data_class("ProcessInfo", ["pid", "start_time"])
    
    
class ProcessSet(object):
    def __init__(self, run_dir, processes):
        # TODO: should rename RunDirectory (process info persistence?)
        self._run_dir = run_dir
        self.run_dir = run_dir._run_dir
        self._processes = processes

    def start(self, commands):
        for name in commands.iterkeys():
            if name in self._processes:
                raise ValueError("Cannot start second process with name {0}".format(name))
        
        self._run_dir.append_names(commands.keys())
        
        def start_process((name, command_args)):
            output_file = self._run_dir.output_path(name)
            command = " ".join(map(_escape_sh, command_args))
            redirected_command = ["sh", "-c", "exec {0} > {1} 2>&1".format(command, output_file)]
            process = local_shell.spawn(redirected_command, store_pid=True)
            process_info = _process_info_for_pid(process.pid)
            self._run_dir.write_process_info(name, process_info)
                
            return (name, process_info)
            
        self._processes.update(map(start_process, commands.iteritems()))

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


class RunDirectory(object):
    def __init__(self, run_dir):
        self._run_dir = run_dir
    
    def append_names(self, names):
        with open(self._names_path(), "a") as names_file:
            for name in names:
                names_file.write("{0}\n".format(name))
    
    def read_names(self):
        with open(self._names_path()) as names_file:
            return [line.strip() for line in names_file.readlines()]
    
    def write_process_info(self, name, process_info):
        with open(self._process_info_path(name), "w") as process_info_file:
            data = {
                "pid": process_info.pid,
                "startTime": process_info.start_time
            }
            json.dump(data, process_info_file)
    
    def read_process_info(self, name):
        with open(self._process_info_path(name)) as process_info_file:
            properties = json.load(process_info_file)
            return ProcessInfo(properties["pid"], properties["startTime"])
    
    def output_path(self, name):
        return os.path.join(self._run_dir, "{0}.output".format(name))

    def _names_path(self):
        return os.path.join(self._run_dir, "names")
        
    def _process_info_path(self, name):
        return os.path.join(self._run_dir, "{0}.process-info".format(name))
