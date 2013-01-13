import contextlib

from selenium import webdriver
import starboard

import peachtree
import peachtree.server
from . import provider_tests
from .qemu_tests import provider_with_temp_data_dir as qemu_provider
from peachtree.sshconfig import SshConfig

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)



@contextlib.contextmanager
def _create_server():
    with qemu_provider() as underlying_provider:
        port = starboard.find_local_free_tcp_port()
        with peachtree.server.start_server(port=port, provider=underlying_provider):
            yield port


@contextlib.contextmanager
def _create_web_provider():
    with _create_server() as port:
        url = "http://localhost:{0}/web/".format(port)
        driver = webdriver.Firefox()
        driver.get(url)
        with WebProvider(driver) as provider:
            yield provider


class WebProvider(object):
    def __init__(self, driver):
        self._driver = driver
        
    def list_available_images(self):
        selector =  "*[data-peachtree='available-images'] tr td:nth-child(2)"
        cells = self._driver.find_elements_by_css_selector(selector)
        return [cell.text for cell in cells]
            
    def start(self, image_name):
        self._start_image(image_name)
        self._view_running_machine()
        
        selector = "*[data-peachtree='view-machine'] *[data-peachtree='ssh-config']"
        ssh_config_text = self._driver.find_element_by_css_selector(selector).text
        return WebMachine(self._read_ssh_config(ssh_config_text))
    
    def _start_image(self, image_name):
        selector = "*[data-peachtree='available-images'] tr"
        for row in self._driver.find_elements_by_css_selector(selector):
            current_image_name = row.find_element_by_css_selector("*[data-peachtree='image-name']").text
            if image_name == current_image_name:
                row.find_element_by_css_selector("input[type='button'][value='Start']").click()
                return
                
        raise RuntimeError("Could not find image with name {0}".format(image_name))
    
    def _view_running_machine(self):
        # TODO: don't assume there's always exactly one running machine!
        self._driver.refresh()
        selector =  "*[data-peachtree='running-machines'] tbody tr"
        row = self._driver.find_element_by_css_selector(selector)
        row.find_element_by_css_selector("input[type='button'][value='View']").click()
    
    def _read_ssh_config(self, text):
        lines = text.split("\n")
        properties = [line.strip().split(" ", 1) for line in lines]
        kwargs = dict((key.lower(), value) for key, value in properties)
        kwargs["port"] = int(kwargs["port"])
        return SshConfig(**kwargs)
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self._driver.close()


class WebMachine(object):
    def __init__(self, ssh_config):
        self._ssh_config = ssh_config
    
    def shell(self):
        return self._ssh_config.shell()
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass

WebTests = provider_tests.create("WebTests", _create_web_provider)
