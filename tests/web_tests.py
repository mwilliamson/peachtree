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
        try:
            dashboard_page = DashboardPage(driver, url)
            yield WebProvider(dashboard_page)
        finally:
            driver.close()


class WebProvider(object):
    def __init__(self, dashboard_page):
        self._dashboard_page = dashboard_page
        
    def list_available_images(self):
        self._dashboard_page.open()
        return [
            image.name()
            for image in self._dashboard_page.available_images()
        ]
            
    def start(self, image_name):
        self._start_image(image_name)
        running_machine = self._view_running_machine()
        return WebMachine(running_machine.ssh_config())
    
    def _start_image(self, image_name):
        self._dashboard_page.open()
        self._dashboard_page.find_available_image(image_name).start()
    
    def _view_running_machine(self):
        # TODO: don't assume there's always exactly one running machine!
        self._dashboard_page.open()
        return self._dashboard_page.running_machines()[0].view()
    

class DashboardPage(object):
    def __init__(self, driver, url):
        self._driver = driver
        self._url = url
        
    def open(self):
        self._driver.get(self._url)
        # TODO: implement appropriate waits
    
    def running_machines(self):
        selector = "*[data-peachtree='running-machines'] tbody tr"
        return [
            RunningMachine(self._driver, element)
            for element in self._driver.find_elements_by_css_selector(selector)
        ]
    
    def available_images(self):
        selector = "*[data-peachtree='available-images'] tr"
        return map(
            AvailableImage,
            self._driver.find_elements_by_css_selector(selector)
        )
    
    def find_available_image(self, image_name):
        for image in self.available_images():
            if image.name() == image_name:
                return image
                
        raise RuntimeError("Could not find image with name {0}".format(image_name))


class RunningMachine(object):
    def __init__(self, driver, element):
        self._driver = driver
        self._element = element

    def view(self):
        selector = "input[type='button'][value='View']"
        self._element.find_element_by_css_selector(selector).click()
        return DetailedMachineView(self._driver)
        
        
class DetailedMachineView(object):
    def __init__(self, driver):
        selector = "*[data-peachtree='view-machine']"
        self._element = driver.find_element_by_css_selector(selector)
        
    def ssh_config(self):
        selector = "*[data-peachtree='ssh-config']"
        ssh_config_text = self._element.find_element_by_css_selector(selector).text
        return WebMachine(self._read_ssh_config_text(ssh_config_text))
    
    def _read_ssh_config_text(self, text):
        lines = text.split("\n")
        properties = [line.strip().split(" ", 1) for line in lines]
        kwargs = dict((key.lower(), value) for key, value in properties)
        kwargs["port"] = int(kwargs["port"])
        return SshConfig(**kwargs)


class AvailableImage(object):
    def __init__(self, row_element):
        self._row_element = row_element
        
    def name(self):
        selector = "*[data-peachtree='image-name']"
        return self._row_element.find_element_by_css_selector(selector).text

    def start(self):
        selector = "input[type='button'][value='Start']"
        self._row_element.find_element_by_css_selector(selector).click()


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
