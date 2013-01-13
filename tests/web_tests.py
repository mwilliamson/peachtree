import contextlib

from selenium import webdriver
import starboard

import peachtree
import peachtree.server
from . import provider_tests
from .qemu_tests import provider_with_temp_data_dir as qemu_provider

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
        yield WebProvider(url)


class WebProvider(object):
    def __init__(self, url):
        self._url = url
        
    def list_available_images(self):
        with self._open() as driver:
            selector =  ".available-images tr td:nth-child(2)"
            cells = driver.find_elements_by_css_selector(selector)
            return [cell.text for cell in cells]
    
    @contextlib.contextmanager
    def _open(self):
        driver = webdriver.Firefox()
        try:
            driver.get(self._url)
            yield driver
        finally:
            driver.close()


WebTests = provider_tests.create("WebTests", _create_web_provider)
