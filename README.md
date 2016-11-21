# cfgfs

FUSE filesystem for wrapping configs from database to readable files

`cfgfs` exposes keys in Redis database into readable files in mountpoint directory. Key names must be valid filenames.

## Usage

Export keys from redis database `1` into `testdir` in user\`s home directory.

```bash
./cfgfs.py redis://localhost:6379/1 ~/testdir
```
