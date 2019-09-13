# class to load GW-BASIC programs
import re
import math
from gwbasic_tokens import tokens

class gwBasicLine:
    """class representing a single line of a GW-BASIC program"""
    def __init__(self, data: bytes, encoding: str, lineStart: int):
        self.data = data
        self.encoding = encoding
        self.lineStart = lineStart
        self.lineNum = 0
    
    # Float binary format: http://www.chebucto.ns.ca/~af380/GW-BASIC-tokens.html
    # Rounding and postfixes: https://www-user.tu-chemnitz.de/~heha/viewchm.php/hs/gwBasic.chm/Chapter6.html
    def ParseFloat32(self, index: int) -> str:
        if self.data[index + 3] == 0:
            return 0

        exp = self.data[index + 3] - 152  #  -152 = -128 + -24 (24 because the significand is behind a decimal dot)
        mantissa = ((self.data[index + 2] | 0x80) << 16) | (self.data[index + 1] << 8) | self.data[index]

        if self.data[index + 2] & 0x80:
            number = -math.ldexp(mantissa, exp)
        else:
            number = math.ldexp(mantissa, exp)

        # Must round to 6 significant figures (from 7) when displaying
        numberStr = self.CanonizeNumber('%s' % float('%.6g' % number))

        # If nothing indicates that this is a float, then add the "!" postfix
        if not ("." in numberStr or "e" in numberStr):
            numberStr += "!"

        return numberStr

    # Double binary format: http://www.chebucto.ns.ca/~af380/GW-BASIC-tokens.html
    # Rounding and postfixes: https://www-user.tu-chemnitz.de/~heha/viewchm.php/hs/gwBasic.chm/Chapter6.html
    def ParseFloat64(self, index: int) -> str:
        if self.data[index + 7] == 0:
            return 0

        exp = self.data[index + 7] - 184  #  -184 = -128 + -56 (56 because the significand is behind a decimal dot)
        mantissa = ((self.data[index + 6] | 0x80) << 48) | (self.data[index + 5] << 40) | (self.data[index + 4] << 32)  \
            | (self.data[index + 3] << 24) | (self.data[index + 2] << 16) | (self.data[index + 1] << 8) | self.data[index]
        
        # We must always output a positive number for doubles,
        # because a token for '-' is already added before the negative ones.
        number = math.ldexp(mantissa, exp)

        # Doubles always get their postfix '#'
        # Must round to 16 significant figures (from 17) when displaying
        numberStr = self.CanonizeNumber('%s' % float('%.16g' % number)) + '#'

        return numberStr

    # For example 8.0 => 8 | 0.21 => .21 | -0.35 => -.35
    def CanonizeNumber(self, num: str) -> str:
        """Make the string representation of numbers follow the GW-Basic standard"""
        num = re.sub(r'^([\-])*0\.', r'\1.', num)
        num = re.sub(r'\.0$', '', num)
        return num

    def Parse(self):
        """Forms a new line from the first line contained in the bytestream.
        Returns a tuple, [gwBasicLine, #bytes consumed]. On error returns None."""

        # first two bytes are address of next line. Mostly irrelevant, but if
        # they're both zero, this is the end of the program.
        if self.data[self.lineStart] == 0 and self.data[self.lineStart + 1] == 0:
            return [None, 2]

        if len(self.data) < 4:
            raise ValueError("Unexpected end of string.")

        # next two bytes are the line number
        self.lineNum = 0x100 * self.data[self.lineStart + 3] + self.data[self.lineStart + 2]
        pos = self.lineStart + 4

        # States that show whether we are inside a REM (comment)
        # statement or inside quotes.
        insideRem = False
        insideQuotes = False

        self._data = []
        # TODO(danvk): be more graceful at unexpected end-of-string
        # TODO(danvk): get signed/unsigned correct
        while self.data[pos] != 0:
            code = self.data[pos]

            if code == 0x22 and not insideRem:  # Quote starts or ends
                # There was no quote escaping. You had to use CHR$() to
                #   output a quote character.
                insideQuotes = not insideQuotes
                self._data.append('"')
                pos += 1
                continue
            elif code == 0x3a and not (insideQuotes or insideRem):
                if len(self.data) - pos > 2:
                    if self.data[pos + 1] == 0x8f and self.data[pos + 2] == 0xd9:
                        # REM block starts
                        # A single quote is an alias for a REM instruction
                        # It is stored with 3 bytes: 0x3a8fd9
                        insideRem = True    # a REM block never ends (inside a line)
                        self._data.append("'")
                        pos += 3
                        continue

            if insideQuotes or insideRem or (code >= 0x20 and code <= 0x7e):
                # Decode the custom texts using the specified code page
                codeByte = code.to_bytes(1, byteorder='little', signed=False)
                self._data.append(codeByte.decode(self.encoding))
                pos += 1
            elif code == 0x8f:     # REM block starts
                insideRem = True    # a REM block never ends (inside a line)
                self._data.append('REM')
                pos += 1
            elif code == 0x0b:    # octal constant (signed)
                val = 0x100 * self.data[pos+2] + self.data[pos+1]
                if val >= 0x8000:
                    val = val - 0x10000
                self._data.append(val)
                pos += 3
            elif code == 0x0c:    # hex constant (signed)
                val = 0x100 * self.data[pos+2] + self.data[pos+1]
                if val >= 0x8000:
                    val = val - 0x10000
                self._data.append(val)
                pos += 3
            elif code == 0x0d:    # line pointer (unsigned)
                raise ValueError("line pointer (0x0d) shouldn't occur in saved program.")
            elif code == 0x0e:    # line number (unsigned)
                self._data.append(0x100 * self.data[pos+2] + self.data[pos+1])
                pos += 3
            elif code == 0x0f:    # one byte constant
                self._data.append(self.data[pos+1])
                pos += 2
            elif code == 0x10:    # Flags constant (unused)
                raise ValueError("unexpected 0x10 token")
            elif code >= 0x11 and code <= 0x1b:
                self._data.append(code - 0x11)
                pos += 1
            elif code == 0x1c:    # two byte data constant (signed?)
                val = 0x100 * self.data[pos+2] + self.data[pos+1]
                if val >= 0x8000:
                    val = val - 0x10000
                self._data.append(val)
                pos += 3
            elif code == 0x1d:    # four byte floating point constant
                self._data.append(self.ParseFloat32(pos + 1))
                pos += 5
            elif code == 0x1e:    # unused
                raise ValueError("unexpected 0x1e token")
            elif code == 0x1f:    # eight byte double value
                self._data.append(self.ParseFloat64(pos + 1))
                pos += 9
            elif code in tokens:
                self._data.append(tokens[code])
                pos += 1
            elif (code * 0x100 + self.data[pos+1]) in tokens:
                self._data.append(tokens[code * 0x100 + self.data[pos+1]])
                pos += 2
            else:
                raise ValueError("unexpected token: %d" % code)

        pos += 1    # consume the null byte
        return [self, pos - self.lineStart]

    def __str__(self):
        return "%5d %s" % (
            self.lineNum, ''.join([str(x) for x in self._data]))


class gwBasic:
    """Class representing a gw-basic program"""

    def __init__(self, data: bytes, encoding: str):
        self.data = data
        self.encoding = encoding
        self.lines = []

        if data[0] != 0xff:
            raise ValueError("Expected 0xff as first character")

    def Parse(self):
        # Form the _lines array by splitting a bytestream on line boundaries.
        pos = 1
        
        while self.data[pos] != 0x1a:
            gwLine = gwBasicLine(self.data, self.encoding, pos)
            line, num_bytes = gwLine.Parse()

            if line is None and num_bytes == 2:
                # This is most likely end of program.
                pos += num_bytes
            elif line is None:
                raise ValueError("Couldn't parse program at position %d" % pos)
            else:
                pos += num_bytes
                self.lines.append(line)

    def __str__(self):
        return "\n".join(str(line) for line in self.lines)
