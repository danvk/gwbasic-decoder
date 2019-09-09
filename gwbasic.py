# class to load GW-BASIC programs
from gwbasic_tokens import tokens


# Parse an encoded float or double. GW-BASIC uses a strange, non-standard
# format. See http://www.chebucto.ns.ca/~af380/GW-BASIC-tokens.html for
# details.
def ParseFloat(bytes):
    exp = bytes[3] - 0x80
    sgn = (bytes[2] & 0x80) >> 8
    mantissa = 0.5 + 1.0 * (((bytes[2] & 0x7f) << 16) + (bytes[1] << 8) + bytes[0]) / 2**24
    return (-1)**sgn * 2**exp * mantissa


def ParseDouble(bytes):
    return "<unparsed double>"
    # return struct.unpack("!d", ''.join([chr(x) for x in bytes[8::-1]]))


class gwbasicline:
    """class representing a single line of a GW-BASIC program"""
    def __init__(self):
        pass

    @staticmethod
    def FromBinary(bytes):
        """Forms a new line from the first line contained in the bytestream.
        Returns a tuple, [gwbasicline, #bytes consumed]. On error returns None."""
        self = gwbasicline()

        # first two bytes are address of next line. Mostly irrelevant, but if
        # they're both zero, this is the end of the program.
        if bytes[0] == 0 and bytes[1] == 0:
            return [None, 2]
        if len(bytes) < 4:
            raise ValueError("Unexpected end of string.")

        # next two bytes are the line number
        self._line_no = 0x100 * bytes[3] + bytes[2]
        pos = 4

        # States that show whether we are inside a REM (comment)
        # statement or inside quotes.
        insideRem = False
        insideQuotes = False

        self._data = []
        # TODO(danvk): be more graceful at unexpected end-of-string
        # TODO(danvk): get signed/unsigned correct
        while bytes[pos] != 0:
            code = bytes[pos]

            if code == 0x22 and not insideRem:  # Quote starts or ends
                # There was no quote escaping. You had to use CHR$() to
                #   output a quote character.
                insideQuotes = not insideQuotes
                self._data.append('"')
                pos += 1
            elif code == 0x8f and not insideQuotes:     # REM block starts
                insideRem = True    # a REM block never ends (inside a line)
                self._data.append('REM')
                pos += 1
            elif insideQuotes or insideRem or (code >= 0x20 and code <= 0x7e):
                # The encoding was probably "IBM Code Page 437"
                # TODO: make the encoding a command line parameter
                self._data.append(chr(code).decode('cp437').encode('utf8'))
                pos += 1
            elif code == 0x0b:    # octal constant (signed)
                val = 0x100 * bytes[pos+2] + bytes[pos+1]
                if val >= 0x8000:
                    val = val - 0x10000
                self._data.append(val)
                pos += 3
            elif code == 0x0c:    # hex constant (signed)
                val = 0x100 * bytes[pos+2] + bytes[pos+1]
                if val >= 0x8000:
                    val = val - 0x10000
                self._data.append(val)
                pos += 3
            elif code == 0x0d:    # line pointer (unsigned)
                raise ValueError("line pointer (0x0d) shouldn't occur in saved program.")
            elif code == 0x0e:    # line number (unsigned)
                self._data.append(0x100 * bytes[pos+2] + bytes[pos+1])
                pos += 3
            elif code == 0x0f:    # one byte constant
                self._data.append(bytes[pos+1])
                pos += 2
            elif code == 0x10:    # Flags constant (unused)
                raise ValueError("unexpected 0x10 token")
            elif code >= 0x11 and code <= 0x1b:
                self._data.append(code - 0x11)
                pos += 1
            elif code == 0x1c:    # two byte data constant (signed?)
                val = 0x100 * bytes[pos+2] + bytes[pos+1]
                if val >= 0x8000:
                    val = val - 0x10000
                self._data.append(val)
                pos += 3
            elif code == 0x1d:    # four byte floating point constant
                # TODO(danvk): parse this
                self._data.append(ParseFloat(bytes[pos+1:pos+5]))
                pos += 5
            elif code == 0x1e:    # unused
                raise ValueError("unexpected 0x1e token")
            elif code == 0x1f:    # eight byte double value
                # TODO(danvk): parse this
                self._data.append(ParseDouble(bytes[pos+1:pos+9]))
                pos += 9
            elif code in tokens:
                self._data.append(tokens[code])
                pos += 1
            elif (code * 0x100 + bytes[pos+1]) in tokens:
                self._data.append(tokens[code * 0x100 + bytes[pos+1]])
                pos += 2
            else:
                raise ValueError("unexpected token: %d" % code)
        pos += 1    # consume the null byte
        return [self, pos]

    def __str__(self):
        return "%5d %s" % (
            self._line_no, ''.join([str(x) for x in self._data]))


class gwbasic:
    """Class representing a gw-basic program"""
    def __init__(self):
        pass

    def Parse(self):
        """Build internal representation of raw_data_"""
        # First byte had better be 0xff = unprotected
        bytes = [ord(x) for x in self._raw_data]
        if bytes[0] != 0xff:
            self.error_ = "Expected 0xff as first character"
            return
        self.SplitLines(bytes)

    def SplitLines(self, bytes):
        # Form the _lines array by splitting a bytestream on line boundaries.
        pos = 1
        self._lines = []
        while bytes[pos] != 0x1a:
            line, num_bytes = gwbasicline.FromBinary(bytes[pos:])
            if line is None and num_bytes == 2:
                # This is most likely end of program.
                pos += num_bytes
            elif line is None:
                raise ValueError("Couldn't parse program at position %d" % pos)
            else:
                pos += num_bytes
                self._lines.append(line)

    @staticmethod
    def FromBinary(data):
        p = gwbasic()
        p._raw_data = data
        p.Parse()
        return p

    def __str__(self):
        return "\n".join(str(line) for line in self._lines)
