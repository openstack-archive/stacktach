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
        value |= image_type.BASE_IMAGE

        self.assertTrue(image_type.isset(value, image_type.BASE_IMAGE))

    def test_isset_snapshot_image(self):
        value = 0
        value |= image_type.SNAPSHOT_IMAGE

        self.assertTrue(image_type.isset(value, image_type.SNAPSHOT_IMAGE))

    def test_isset_linux_image(self):
        value = 0
        value |= image_type.LINUX_IMAGE

        self.assertTrue(image_type.isset(value, image_type.LINUX_IMAGE))

    def test_isset_windows_image(self):
        value = 0
        value |= image_type.WINDOWS_IMAGE

        self.assertTrue(image_type.isset(value, image_type.WINDOWS_IMAGE))

    def test_isset_os_debian(self):
        value = 0
        value |= image_type.OS_DEBIAN

        self.assertTrue(image_type.isset(value, image_type.OS_DEBIAN))

    def test_isset_os_ubuntu(self):
        value = 0
        value |= image_type.OS_UBUNTU

        self.assertTrue(image_type.isset(value, image_type.OS_UBUNTU))

    def test_isset_os_centos(self):
        value = 0
        value |= image_type.OS_CENTOS

        self.assertTrue(image_type.isset(value, image_type.OS_CENTOS))

    def test_isset_os_rhel(self):
        value = 0
        value |= image_type.OS_RHEL

        self.assertTrue(image_type.isset(value, image_type.OS_RHEL))

    def test_get_numeric_code(self):
        payload = {
            "image_meta": {
                "image_type": "base",
                "os_type": "linux",
                "os_distro": "centos"
            }
        }

        result = image_type.get_numeric_code(payload, 0)

        self.assertEqual(result, 0x411)

    def test_readable(self):
        value = 0x111

        result = image_type.readable(value)

        self.assertEqual(result, ['base', 'linux', 'ubuntu'])

    def test_false_isset_base_image_from_payload(self):
        value = 0
        value |= image_type.SNAPSHOT_IMAGE

        self.assertFalse(image_type.isset(value, image_type.BASE_IMAGE))

    def test_false_isset_snapshot_image(self):
        value = 0
        value |= image_type.BASE_IMAGE

        self.assertFalse(image_type.isset(value, image_type.SNAPSHOT_IMAGE))

    def test_false_isset_linux_image(self):
        value = 0
        value |= image_type.WINDOWS_IMAGE

        self.assertFalse(image_type.isset(value, image_type.LINUX_IMAGE))

    def test_false_isset_windows_image(self):
        value = 0
        value |= image_type.LINUX_IMAGE

        self.assertFalse(image_type.isset(value, image_type.WINDOWS_IMAGE))

    def test_false_isset_os_debian(self):
        value = 0
        value |= image_type.OS_UBUNTU

        self.assertFalse(image_type.isset(value, image_type.OS_DEBIAN))

    def test_false_isset_os_ubuntu(self):
        value = 0
        value |= image_type.OS_RHEL

        self.assertFalse(image_type.isset(value, image_type.OS_UBUNTU))

    def test_false_isset_os_rhel(self):
        value = 0
        value |= image_type.OS_DEBIAN

        self.assertFalse(image_type.isset(value, image_type.OS_RHEL))

    def test_false_isset_os_centos(self):
        value = 0
        value |= image_type.OS_UBUNTU

        self.assertFalse(image_type.isset(value, image_type.OS_CENTOS))

    def test_blank_argument_isset(self):
        self.assertFalse(image_type.isset(None, image_type.OS_CENTOS))
