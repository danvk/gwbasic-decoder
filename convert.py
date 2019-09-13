#!/usr/bin/env python
# Convert a binary GW-BASIC program into human-readable ASCII.

import sys
import codecs
import traceback
from gwBasic import gwBasic

if __name__ == '__main__':
    # Check the number of parameters
    if not (2 <= len(sys.argv) <= 3):
        sys.stderr.writelines([
            "\nUsage:\n",
            "\t./convert.py FILE.BAS [character encoding] > textfile.bas\n\n",
            "Example encodings:\n",
            "\t- cp437 (IBM original, default), cp850 (Latin-1), cp1252 (Windows 1.0 and later)\n",
            "\t  iso-8859-1 (Western Europe), and all the others supported by Python.\n\n"
        ])
        sys.exit(1)

    # Default encoding if nothing specified
    encoding = "cp437"

    try:
        if len(sys.argv) == 3:
            try:
                codecs.lookup(sys.argv[2])
                encoding = sys.argv[2]
            except LookupError:
                raise ValueError("Unknown character encoding: %s" % sys.argv[2])
        
        filename = sys.argv[1]
        with open(filename, 'rb') as f:
            data = f.read()
            program = gwBasic(data, encoding)
            program.Parse()
            print(program)

    except Exception as ex:
        sys.stdout.write("\n%s\n\n" % traceback.format_exc())
        sys.exit(1)
