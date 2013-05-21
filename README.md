# peachtree

Python library for interacting with [QEMU](http://qemu.org/).

## Commands

### run

    peachtree run <image-name> [--public-port=<port>]

Run the image `<image-name>`.
Optionally specify one or more ports that should be made public.
For instance, by specifying `--public-port=22`,
port 22 on the guest will be forwarded to an available port on the host.
A description of the machine will be printed out once the machine is ready.

### stop

    peachtree stop <identifier>

Stop the machine identified by `<identifier>`.

### describe

    peachtree describe <identifier>

Describe the machine identified by `<identifier>`.

### describe-all

    peachtree describe-all

Describe all running machines.

## Images

When using the QEMU provider,
Peachtree expects images to be stored under
`$XDG_DATA_HOME/peachtree-0.3/qemu/images`
(`$XDG_DATA_HOME` defaults to `~/.local/share`).

Each image should have its own directory.
The directory should contain a JSON file called image.json with the following
properties:

* `disks`: an array of paths to the disk images that should be used,
  relative to the image directory.

* `memory` (optional): the amount of memory to allocate to the virtual machine.
  Defaults to 512MB.

* `users` (optional):
  the list of users that can be used to log into the machine.
  Each user should have three properties:
  `username` (string), `password` (string), and `is_root` (boolean).
  Defaults to an ordinary user `qemu-user` with the password `password1`,
  and a root user `root` with the password `password1`.

* `sshPort` (optional): the port that SSH uses on the guest.
  Defaults to 22.
