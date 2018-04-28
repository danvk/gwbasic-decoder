#!/usr/bin/env python
# Convert a binary GW-BASIC program into human-readable ASCII.

import sys
from gwbasic import gwbasic

if __name__ == '__main__':
    assert len(sys.argv) == 2
    filename = sys.argv[1]
    with open(filename, 'r') as f:
        data = f.read()
        program = gwbasic.FromBinary(data)
        print program
