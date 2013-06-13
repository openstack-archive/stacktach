# Copyright (c) 2012 - Rackspace Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import unittest

from stacktach import image_type


class ImageTypeTestCase(unittest.TestCase):

    def test_isset_base_image(self):
        value = 0
        expected = True
        value |= image_type.BASE_IMAGE
        result = image_type.isset(value, image_type.BASE_IMAGE)
        self.assertEqual(result, expected)

    def test_isset_snapshot_image(self):
        value = 0
        expected = True
        value |= image_type.SNAPSHOT_IMAGE
        result = image_type.isset(value, image_type.SNAPSHOT_IMAGE)
        self.assertEqual(result, expected)

    def test_isset_linux_image(self):
        value = 0
        expected = True
        value |= image_type.LINUX_IMAGE
        result = image_type.isset(value, image_type.LINUX_IMAGE)
        self.assertEqual(result, expected)

    def test_isset_windows_image(self):
        value = 0
        expected = True
        value |= image_type.WINDOWS_IMAGE
        result = image_type.isset(value, image_type.WINDOWS_IMAGE)
        self.assertEqual(result, expected)

    def test_isset_os_debian(self):
        value = 0
        expected = True
        value |= image_type.OS_DEBIAN
        result = image_type.isset(value, image_type.OS_DEBIAN)
        self.assertEqual(result, expected)

    def test_isset_os_ubuntu(self):
        value = 0
        expected = True
        value |= image_type.OS_UBUNTU
        result = image_type.isset(value, image_type.OS_UBUNTU)
        self.assertEqual(result, expected)

    def test_isset_os_centos(self):
        value = 0
        expected = True
        value |= image_type.OS_CENTOS
        result = image_type.isset(value, image_type.OS_CENTOS)
        self.assertEqual(result, expected)

    def test_isset_os_rhel(self):
        value = 0
        expected = True
        value |= image_type.OS_RHEL
        result = image_type.isset(value, image_type.OS_RHEL)
        self.assertEqual(result, expected)

    def test_get_numeric_code(self):
        payload = {
            "image_meta": {
                "image_type": "base",
                "os_type": "linux",
                "os_distro": "ubuntu"
            }
        }
        expected = 0x111
        result = image_type.get_numeric_code(payload, 0)
        self.assertEqual(result, expected)

    def test_readable(self):
        value = 0x111
        expected = ['base', 'linux', 'ubuntu']
        result = image_type.readable(value)
        self.assertEqual(result, expected)

    def test_windows_image_from_payload(self):
        payload = {
            "image_meta": {
                "image_type": "base",
                "os_type": "windows",
                "os_distro": ""
            }
        }
        expected = True
        type_code = image_type.get_numeric_code(payload, 0)
        result = image_type.isset(type_code, image_type.WINDOWS_IMAGE)
        self.assertEqual(result, expected)

    def test_linux_image_from_payload(self):
        payload = {
            "image_meta": {
                "image_type": "base",
                "os_type": "linux",
                "os_distro": "debian"
            }
        }
        expected = True
        type_code = image_type.get_numeric_code(payload, 0)
        result = image_type.isset(type_code, image_type.LINUX_IMAGE)
        self.assertEqual(result, expected)

    def test_base_image_from_payload(self):
        payload = {
            "image_meta": {
                "image_type": "base",
                "os_type": "linux",
                "os_distro": "debian"
            }
        }
        expected = True
        type_code = image_type.get_numeric_code(payload, 0)
        result = image_type.isset(type_code, image_type.BASE_IMAGE)
        self.assertEqual(result, expected)

    def test_snapshot_image_from_payload(self):
        payload = {
            "image_meta": {
                "image_type": "snapshot",
                "os_type": "linux",
                "os_distro": "debian"
            }
        }
        expected = True
        type_code = image_type.get_numeric_code(payload, 0)
        result = image_type.isset(type_code, image_type.SNAPSHOT_IMAGE)
        self.assertEqual(result, expected)
