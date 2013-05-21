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
