# cfgfs

FUSE filesystem for wrapping configs from database to readable files

`cfgfs` exposes keys in Redis database into readable files in mountpoint directory. Key names must be valid filenames.

## Usage

Export keys from redis database `1` into `testdir` in user\`s home directory:

```bash
./cfgfs.py redis://localhost:6379/1 ~/testdir
```

Keys from Redis database 1 will be available in `testdir` directory:

```
$ redis-cli -n 1 --scan
newfile
test
hello
$ ls ~/testdir/
hello  newfile  test
$ redis-cli -n 1 get hello
"world"
$ cat ~/testdir/hello ; echo
world
```

## Automounting using /etc/fstab

Here `/PATH/TO/cfgfs.py` is actual path to `cfgfs.py` and `/PATH/TO/MOUNTPOINT` is actual path to directory where filesystem should be mounted. Redis URL has to be changed with your actual Redis connect string. 

### Option 1

Add line to `/etc/fstab`:

```
/PATH/TO/cfgfs.py#redis://localhost:6379/0   /PATH/TO/MOUNTPOINT   fuse    auto    0   0
```

### Option 2

Run following as root to create symlinks and make `cfgfs` filesystem known to your OS:

```bash
ln -sf /PATH/TO/cfgfs.py /usr/sbin/mount.cfgfs
ln -sf /PATH/TO/cfgfs.py /sbin/mount.cfgfs
```

Then add mount line in `/etc/fstab` like for usual filesystem: 

```
redis://localhost:6379/0   /PATH/TO/MOUNTPOINT   cfgfs    auto    0   0
```
