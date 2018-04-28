#!/usr/bin/python2.4
# Convert a binary GW-BASIC program into human-readable ASCII.

import sys
from gwbasic import gwbasic

if __name__ == '__main__':
  assert len(sys.argv) == 2
  filename = sys.argv[1];
  f = open(filename, "r")
  data = f.read()
  f.close()
  program = gwbasic.FromBinary(data)
  print program
