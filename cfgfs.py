#!/usr/bin/env python
import sys
import os
import logging
import redis

import errno
from stat import S_IFDIR, S_IFREG
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context

POOL_TIMEOUT=3
CONN_TIMEOUT=3

class CfgFS(LoggingMixIn, Operations):
    def __init__(self, redis_url):
        self._redis_pool = redis.BlockingConnectionPool.from_url(
            redis_url, timeout = POOL_TIMEOUT) 

        self._uid = os.getuid()
        self._gid = os.getgid()
        self._files = {}

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
            r = redis.StrictRedis(connection_pool = self._redis_pool)
            if path[0] == '/' and r.exists(key):
                size = r.strlen(key)
                st = {
                    'st_mode': (S_IFREG | 0o444),
                    'st_size': size,
                    'st_uid': self._uid,
                    'st_gid': self._gid,
                    'st_nlink': 1
                }
            else:
                raise FuseOSError(errno.ENOENT)
        st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
        return st

    def read(self, path, size, offset, fh):
        if fh in self._files:
            return self._files[fh][offset:(offset+size)]
        else:
            raise FuseOSError(errno.EBADFD)

    def readdir(self, path, fh):
        if path == '/':
            r = redis.StrictRedis(connection_pool = self._redis_pool)
            keys = list(set(r.scan_iter()))
            return ['.', '..'] + keys
        else:
            raise FuseOSError(errno.ENOENT)

    def open(self, path, flags):
        key = path[1:]
        r = redis.StrictRedis(connection_pool = self._redis_pool)
        data = r.get(key)
        if data is None:
            raise FuseOSError(errno.ENOENT)

        fn = 0
        while fn in self._files:
            fn += 1
        self._files[fn] = data
        return fn

    def release(self, path, fh):
        self._files.pop(fh, None)


    # Disable unused operations:
    access = None
    flush = None
    getxattr = None
    listxattr = None
    opendir = None
    releasedir = None
    statfs = None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: %s <mountpoint> <redis URL>' % sys.argv[0])
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG)

    fuse = FUSE(CfgFS(sys.argv[2]), sys.argv[1], foreground=True, ro=True, allow_other=True, nonempty=True)
