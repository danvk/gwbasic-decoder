#!/usr/bin/env python3
# Convert a binary GW-BASIC program into human-readable ASCII.

import sys
import codecs
import argparse
from gwbasic import GWBasic

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts binary GW-Basic source files to UTF-8 encoded texts.')
    parser.add_argument('source_file', metavar="SOURCE.BAS", type=str, help="A binary GW-Basic source file to be converted to text")
    parser.add_argument('--encoding', metavar="cp437", type=str, help="The encoding of the source file. Examples: " \
        "cp437 (IBM original, default), cp850 (Latin-1), cp1252 (Windows 1.0 and later), " \
        "iso-8859-1 (Western Europe), and all the others supported by Python.", default="cp437", required=False)
    args = parser.parse_args()

    try:
        codecs.lookup(args.encoding)
    except LookupError:
        raise ValueError("Unknown character encoding: %s" % args.encoding)
    
    with open(args.source_file, 'rb') as f:
        data = f.read()
        program = GWBasic(data, args.encoding)
        program.parse()
        print(program)
