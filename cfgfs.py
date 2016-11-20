#!/usr/bin/env python
import sys
import os
import logging

from errno import ENOENT
from stat import S_IFDIR, S_IFREG
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context


class CfgFS(LoggingMixIn, Operations):
    def __init__(self):
        self._uid = os.getuid()
        self._gid = os.getgid()
        self.cfg = {
            'a': 123123123,
            'bbb': 'glk13grj13gijioqwroroijgoqreegq',
            'c': '232ewedfwffdsfsdf2fefwef',
            'hello': 'world',
        }

    def getattr(self, path, fh=None):
        if path == '/':
            st = {
                'st_mode': (S_IFDIR | 0o555),
                'st_uid': self._uid,
                'st_gid': self._gid,
                'st_nlink': 2
            }
        else:
            key = path[1:]
            if path[0] == '/' and key in self.cfg:
                size = len(str(self.cfg[path[1:]]))
                st = {
                    'st_mode': (S_IFREG | 0o444),
                    'st_size': size,
                    'st_uid': self._uid,
                    'st_gid': self._gid,
                    'st_nlink': 1
                }
            else:
                raise FuseOSError(ENOENT)
        st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
        return st

    def read(self, path, size, offset, fh):
        key = path[1:]
        if path[0] == '/' and key in self.cfg:
            return str(self.cfg[key])[offset:(offset+size)]
        else:
            raise RuntimeError('unexpected path: %r' % path)

    def readdir(self, path, fh):
        if path == '/':
            return ['.', '..'] + self.cfg.keys()
        else:
            raise RuntimeError('unexpected path: %r' % path)

    # Disable unused operations:
    access = None
    flush = None
    getxattr = None
    listxattr = None
    open = None
    opendir = None
    release = None
    releasedir = None
    statfs = None


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG)

    fuse = FUSE(CfgFS(), sys.argv[1], foreground=True, ro=True, allow_other=True, nonempty=True)
