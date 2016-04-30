
A system to automate building on MUCKs (and possibly similar systems; it would probably not be too much effort to go through and change the exact commands produced.) Sets of rooms and exits are specified with YAML. The program produces commands that can be used to build, un-build and 'update' the whole project or parts of it. See `test.yaml`. You can use this to write a project in structured form and then build it automatically.

It's also easy to use as a back-end for generating rooms programmatically. Just write a program that produces the appropriate data structure and dumps it to a `.yaml` file. One such program is included to demonstrate.

Requires Python 3 and the `yaml` module (`pacman -S python-yaml` on Arch Linux, or etc.)

