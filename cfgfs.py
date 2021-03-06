#!/usr/bin/env python
import sys
import os
import os.path
import logging
import logging.handlers
import redis

import errno
from stat import S_IFDIR, S_IFREG
from time import time

logging._acquireLock()
try:
    OldLoggerClass = logging.getLoggerClass()
    class LoggerTemplate(OldLoggerClass):
        def __init__(self, name):
            OldLoggerClass.__init__(self, "cfgfs")
            handler = logging.handlers.SysLogHandler(address = '/dev/log')
            handler.setFormatter(logging.Formatter("%(name)s:%(levelname)s:%(message)s"))
            self.addHandler(handler)
    logging.setLoggerClass(LoggerTemplate)
finally:
    logging._releaseLock()

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context

POOL_TIMEOUT=3
CONN_TIMEOUT=3

class CfgFS(LoggingMixIn, Operations):
    class _opened_file(object):
        def __init__(self, data, ts):
            self.data = data
            self.ts = ts

    def __init__(self, redis_url):
        self._redis_pool = redis.BlockingConnectionPool.from_url(
            redis_url, timeout = POOL_TIMEOUT) 

        self._uid = os.getuid()
        self._gid = os.getgid()
        self._files = {}

    def getattr(self, path, fh=None):
        if fh in self._files:
            return {
                'st_mode': (S_IFREG | 0o444),
                'st_size': len(self._files[fh].data),
                'st_uid': self._uid,
                'st_gid': self._gid,
                'st_nlink': 1,
                'st_ctime': self._files[fh].ts,
                'st_mtime': self._files[fh].ts,
                'st_atime': self._files[fh].ts,
            }

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
            return self._files[fh].data[offset:(offset+size)]
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
        self._files[fn] = self._opened_file(data, time())
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
        print('usage: %s <redis URL> <mountpoint>' % sys.argv[0])
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG)

    fuse = FUSE(CfgFS(sys.argv[1]), sys.argv[2], foreground=False, ro=True, allow_other=True, nonempty=True)
