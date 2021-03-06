#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Tests for Hadoop FS.
"""
from nose.tools import assert_false, assert_true, assert_equals, assert_raises, assert_not_equals
from nose.plugins.attrib import attr
import logging
import posixfile
import random
from threading import Thread

from hadoop import pseudo_hdfs4
from hadoop.fs.exceptions import WebHdfsException
from hadoop.fs.hadoopfs import Hdfs

LOG = logging.getLogger(__name__)

@attr('requires_hadoop')
def test_webhdfs():
  """
  Minimal tests for a few basic file system operations.
  """
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)
  f = fs.open("/fortest.txt", "w")
  try:
    f.write("hello")
    f.close()
    assert_equals("hello", fs.open("/fortest.txt").read())
    assert_equals(5, fs.stats("/fortest.txt")["size"])
    assert_true(fs.isfile("/fortest.txt"))
    assert_false(fs.isfile("/"))
    assert_true(fs.isdir("/"))
    assert_false(fs.isdir("/fortest.txt"))
  finally:
    fs.remove("/fortest.txt")

@attr('requires_hadoop')
def test_webhdfs_functions():
  """
  Tests advanced file system operations.
  """
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)

  # Create home dir
  fs.create_home_dir("/user/test")
  assert_true(fs.isdir("/user/test"))
  fs.remove("/user/test")

@attr('requires_hadoop')
def test_seek():
  """Test for DESKTOP-293 - ensure seek works in python2.4"""
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)
  f = fs.open("/fortest.txt", "w")
  try:
    f.write("hello")
    f.close()

    f = fs.open("/fortest.txt", "r")
    f.seek(0, posixfile.SEEK_SET)
    assert_equals("he", f.read(2))
    f.seek(1, posixfile.SEEK_SET)
    assert_equals("el", f.read(2))
    f.seek(-1, posixfile.SEEK_END)
    assert_equals("o", f.read())
    f.seek(0, posixfile.SEEK_SET)
    f.seek(2, posixfile.SEEK_CUR)
    assert_equals("ll", f.read(2))
  finally:
    fs.remove("/fortest.txt")

@attr('requires_hadoop')
def test_seek_across_blocks():
  """Makes a file with a lot of blocks, seeks around"""
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)
  fs.create("/fortest-blocks.txt", replication=1, blocksize=1024)
  f = fs.open("/fortest-blocks.txt", "w")
  try:
    data = "abcdefghijklmnopqrstuvwxyz" * 3000
    f.write(data)
    f.close()

    for i in xrange(1, 10):
      f = fs.open("/fortest-blocks.txt", "r")

      for j in xrange(1, 100):
        offset = random.randint(0, len(data) - 1)
        f.seek(offset, posixfile.SEEK_SET)
        assert_equals(data[offset:offset+50], f.read(50))
      f.close()

  finally:
    fs.remove("/fortest-blocks.txt")

@attr('requires_hadoop')
def test_exceptions():
  """
  Tests that appropriate exceptions are raised.
  """
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)
  f = fs.open("/for_exception_test.txt", "w")
  f.write("foo")
  f.close()
  fs.chmod("/for_exception_test.txt", 0400)
  fs.setuser("notsuperuser")
  f = fs.open("/for_exception_test.txt")

  assert_raises(WebHdfsException, f.read)
  assert_raises(IOError, fs.open, "/test/doesnotexist.txt")

@attr('requires_hadoop')
def test_copy_remote_dir():
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)

  src_dir = '/copy_remote_dir'
  fs.mkdir(src_dir)
  f1 = fs.open("/copy_remote_dir/test_one.txt", "w")
  f1.write("foo")
  f1.close()
  f2 = fs.open("/copy_remote_dir/test_two.txt", "w")
  f2.write("bar")
  f2.close()

  new_owner = 'testcopy'
  new_owner_home = '/user/testcopy'
  new_owner_dir = new_owner_home + '/test-copy'
  fs.mkdir(new_owner_home)
  fs.chown(new_owner_home, new_owner, new_owner)

  fs.copy_remote_dir(src_dir, new_owner_dir, dir_mode=0755, owner=new_owner)

  dir_stat = fs.stats(new_owner_dir)
  assert_equals(new_owner, dir_stat.user)
  assert_equals(new_owner, dir_stat.group)
  assert_equals('40755', '%o' % dir_stat.mode)

  src_stat = fs.listdir_stats(src_dir)
  dest_stat = fs.listdir_stats(new_owner_dir)

  src_names = set([stat.name for stat in src_stat])
  dest_names = set([stat.name for stat in dest_stat])
  assert_true(src_names)
  assert_equals(src_names, dest_names)

  for stat in dest_stat:
    assert_equals('testcopy', stat.user)
    assert_equals('testcopy', stat.group)
    assert_equals('100644', '%o' % stat.mode)

@attr('requires_hadoop')
def test_two_files_open():
  """
  See DESKTOP-510.  There was a bug where you couldn't open two files at
  the same time.  It boils down to a close_fds=True issue.  If this doesn't
  hang, all is good.
  """
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)
  f1 = fs.open("/test_one.txt", "w")
  f2 = fs.open("/test_two.txt", "w")
  f1.write("foo")
  f2.write("bar")
  f1.close()
  f2.close()
  # This should work, not hang, etc.


def test_urlsplit():
  """Test Hdfs urlsplit"""
  url = 'hdfs://nn.no.port/foo/bar'
  assert_equals(('hdfs', 'nn.no.port', '/foo/bar', '', ''), Hdfs.urlsplit(url))
  url = 'hdfs://nn:8020/foo/bar'
  assert_equals(('hdfs', 'nn:8020', '/foo/bar', '', ''), Hdfs.urlsplit(url))
  url = 'hdfs://nn:8020//foo//bar'
  assert_equals(('hdfs', 'nn:8020', '/foo/bar', '', ''), Hdfs.urlsplit(url))
  url = 'hdfs://nn:8020'
  assert_equals(('hdfs', 'nn:8020', '/', '', ''), Hdfs.urlsplit(url))
  url = '/foo/bar'
  assert_equals(('hdfs', '', '/foo/bar', '', ''), Hdfs.urlsplit(url))
  url = 'foo//bar'
  assert_equals(('hdfs', '', 'foo/bar', '', ''), Hdfs.urlsplit(url))


@attr('requires_hadoop')
def test_i18n_namespace():
  cluster = pseudo_hdfs4.shared_cluster()
  cluster.fs.setuser(cluster.superuser)

  def check_existence(name, parent, present=True):
    assertion = present and assert_true or assert_false
    listing = cluster.fs.listdir(parent)
    assertion(name in listing, "%s should be in %s" % (name, listing))

  name = u'''pt-Olá_ch-你好_ko-안녕_ru-Здравствуйте%20,.<>~`!@#$%^&()_-+='"'''
  prefix = '/tmp/i18n'
  dir_path = '%s/%s' % (prefix, name)
  file_path = '%s/%s' % (dir_path, name)

  try:
    # Create a directory
    cluster.fs.mkdir(dir_path)
    # Directory is there
    check_existence(name, prefix)

    # Create a file (same name) in the directory
    cluster.fs.open(file_path, 'w').close()
    # File is there
    check_existence(name, dir_path)

    # Test rename
    new_file_path = file_path + '.new'
    cluster.fs.rename(file_path, new_file_path)
    # New file is there
    check_existence(name + '.new', dir_path)

    # Test remove
    cluster.fs.remove(new_file_path)
    check_existence(name + '.new', dir_path, present=False)

    # Test rmtree
    cluster.fs.rmtree(dir_path)
    check_existence(name, prefix, present=False)

    # Test exception can handle non-ascii characters
    try:
      cluster.fs.rmtree(dir_path)
    except IOError, ex:
      LOG.info('Successfully caught error: %s' % (ex,))
  finally:
    try:
      cluster.fs.rmtree(prefix)
    except Exception, ex:
      LOG.error('Failed to cleanup %s: %s' % (prefix, ex))

@attr('requires_hadoop')
def test_threadedness():
  # Start a second thread to change the user, and
  # make sure that isn't reflected.
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser("alpha")
  class T(Thread):
    def run(self):
      fs.setuser("beta")
      assert_equals("beta", fs.user)
  t = T()
  t.start()
  t.join()
  assert_equals("alpha", fs.user)
  fs.setuser("gamma")
  assert_equals("gamma", fs.user)

@attr('requires_hadoop')
def test_chmod():
  # Create a test directory with
  # a subdirectory and a few files.
  dir1 = '/test'
  subdir1 = dir1 + '/test1'
  file1 = subdir1 + '/test1.txt'
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)
  try:
    fs.mkdir(subdir1)
    f = fs.open(file1, "w")
    f.write("hello")
    f.close()

    # Check currrent permissions are not 777 (666 for file)
    fs.chmod(dir1, 01000, recursive=True)
    assert_equals(041000, fs.stats(dir1).mode)
    assert_equals(041000, fs.stats(subdir1).mode)
    assert_equals(0100000, fs.stats(file1).mode)

    # Chmod non-recursive
    fs.chmod(dir1, 01222, recursive=False)
    assert_equals(041222, fs.stats(dir1).mode)
    assert_equals(041000, fs.stats(subdir1).mode)
    assert_equals(0100000, fs.stats(file1).mode)

    # Chmod recursive
    fs.chmod(dir1, 01444, recursive=True)
    assert_equals(041444, fs.stats(dir1).mode)
    assert_equals(041444, fs.stats(subdir1).mode)
    assert_equals(0100444, fs.stats(file1).mode)
  finally:
    try:
      fs.rmtree(dir1)
    finally:
      pass

@attr('requires_hadoop')
def test_chown():
  # Create a test directory with
  # a subdirectory and a few files.
  dir1 = '/test'
  subdir1 = dir1 + '/test1'
  file1 = subdir1 + '/test1.txt'
  cluster = pseudo_hdfs4.shared_cluster()
  fs = cluster.fs
  fs.setuser(cluster.superuser)
  try:
    fs.mkdir(subdir1)
    f = fs.open(file1, "w")
    f.write("hello")
    f.close()

    # Check currrent owners are not user test
    LOG.info(str(fs.stats(dir1).__dict__))
    assert_not_equals('test', fs.stats(dir1).user)
    assert_not_equals('test', fs.stats(subdir1).user)
    assert_not_equals('test', fs.stats(file1).user)

    # Chown non-recursive
    fs.chown(dir1, 'test', recursive=False)
    assert_equals('test', fs.stats(dir1).user)
    assert_not_equals('test', fs.stats(subdir1).user)
    assert_not_equals('test', fs.stats(file1).user)

    # Chown recursive
    fs.chown(dir1, 'test', recursive=True)
    assert_equals('test', fs.stats(dir1).user)
    assert_equals('test', fs.stats(subdir1).user)
    assert_equals('test', fs.stats(file1).user)
  finally:
    try:
      fs.rmtree(dir1)
    finally:
      pass