# class to load GW-BASIC programs
import re
import math
from gwbasic_tokens import tokens

class GWBasicLine:
    """class representing a single line of a GW-BASIC program"""
    def __init__(self, data: bytes, encoding: str, lineStart: int):
        self._data = data
        self._encoding = encoding
        self._lineStart = lineStart
        self._lineNum = 0
        self._lineBuffer = []
        self.isEOF = False
        self._pos = lineStart
    
    # Float binary format: http://www.chebucto.ns.ca/~af380/GW-BASIC-tokens.html
    # Rounding and postfixes: https://www-user.tu-chemnitz.de/~heha/viewchm.php/hs/gwBasic.chm/Chapter6.html
    def _parse_float32(self, index: int) -> str:
        if self._data[index + 3] == 0:
            return "0"

        exp = self._data[index + 3] - 152  #  -152 = -128 + -24 (24 because the significand is behind a decimal dot)
        mantissa = ((self._data[index + 2] | 0x80) << 16) | (self._data[index + 1] << 8) | self._data[index]

        if self._data[index + 2] & 0x80:
            number = -math.ldexp(mantissa, exp)
        else:
            number = math.ldexp(mantissa, exp)

        # Must round to 6 significant figures (from 7) when displaying
        numberStr = self._canonize_number('%s' % float('%.6g' % number))

        # If nothing indicates that this is a float, then add the "!" postfix
        if not ("." in numberStr or "E" in numberStr):
            numberStr += "!"

        return numberStr

    # Double binary format: http://www.chebucto.ns.ca/~af380/GW-BASIC-tokens.html
    # Rounding and postfixes: https://www-user.tu-chemnitz.de/~heha/viewchm.php/hs/gwBasic.chm/Chapter6.html
    def _parse_float64(self, index: int) -> str:
        if self._data[index + 7] == 0:
            return "0"

        exp = self._data[index + 7] - 184  #  -184 = -128 + -56 (56 because the significand is behind a decimal dot)
        mantissa = ((self._data[index + 6] | 0x80) << 48) | (self._data[index + 5] << 40) | (self._data[index + 4] << 32)  \
            | (self._data[index + 3] << 24) | (self._data[index + 2] << 16) | (self._data[index + 1] << 8) | self._data[index]
        
        # We must always output a positive number for doubles,
        # because a token for '-' is already added before the negative ones.
        number = math.ldexp(mantissa, exp)

        # Must round to 16 significant figures (from 17) when displaying
        # The exponent sign for doubles is 'D' instead of 'E'
        numberStr = self._canonize_number('%s' % float('%.16g' % number)).replace('E', 'D')
        
        # Doubles only get their postfix '#' when they don't contain the exponentiation letter 'D'
        if "D" not in numberStr:
            numberStr += "#"

        return numberStr

    # For example 8.0 => 8 | 0.21 => .21 | -0.35 => -.35 | 1.7e-5 => 1.7E-5
    def _canonize_number(self, num: str) -> str:
        """Make the string representation of numbers follow the GW-Basic standard"""
        num = re.sub(r'^([\-])*0\.', r'\1.', num)
        num = re.sub(r'\.0$', '', num)
        return num.upper()  # Make the "e" exponent upper-case "E"

    def get_consumed_byte_count(self) -> int:
        return self._pos - self._lineStart

    def _check_boundary(self, required: int):
        if len(self._data) - self._pos - 1 < required:
            if self._lineNum > 0:
                raise Exception("Unexpected end of file after line %d" % self._lineNum)
            else:
                raise Exception("Unexpected end of file at byte position %s" % hex(self._pos))

    def parse(self):
        """Forms a new line from the first line contained in the bytestream."""

        self._check_boundary(2)

        # first two bytes are address of next line. Mostly irrelevant, but if
        # they're both zero, this is the end of the program.
        if self._data[self._pos] == 0 and self._data[self._pos + 1] == 0:
            self.isEOF = True
            return
        
        self._pos += 2
        self._check_boundary(2)

        # next two bytes are the line number
        self._lineNum = (self._data[self._pos + 1] << 8) | self._data[self._pos]
        self._pos += 2

        # States that show whether we are inside a REM (comment)
        # statement or inside quotes.
        insideRem = False
        insideQuotes = False

        while self._data[self._pos] != 0:
            self._check_boundary(1)
            code = self._data[self._pos]

            if code == 0x22 and not insideRem:  # Quote starts or ends
                # There was no quote escaping. You had to use CHR$() to
                #   output a quote character.
                insideQuotes = not insideQuotes
                self._lineBuffer.append('"')
                self._pos += 1
            elif code == 0x3a and not (insideQuotes or insideRem) and (len(self._data) - self._pos - 1 > 2) \
                and self._data[self._pos + 1] == 0x8f and self._data[self._pos + 2] == 0xd9:
                    # REM block starts
                    # A single quote is an alias for a REM instruction
                    # It is stored with 3 bytes: 0x3a8fd9
                    insideRem = True    # a REM block never ends (inside a line)
                    self._lineBuffer.append("'")
                    self._pos += 3
            elif insideQuotes or insideRem or (code >= 0x20 and code <= 0x7e):
                # Decode the custom texts using the specified code page
                codeByte = code.to_bytes(1, byteorder='little', signed=False)
                self._lineBuffer.append(codeByte.decode(self._encoding))
                self._pos += 1
            elif code == 0x8f:     # REM block starts
                insideRem = True    # a REM block never ends (inside a line)
                self._lineBuffer.append('REM')
                self._pos += 1
            elif code == 0x0b:    # octal constant
                # signed, but that's not visible in octal representation
                self._check_boundary(2)
                value = (self._data[self._pos + 2] << 8) | self._data[self._pos + 1]
                numerals = []

                while value > 0:
                    numerals.append(str(value & 0x07))
                    value = value >> 3

                if len(numerals) < 1:
                    numerals.append("0")

                numerals.reverse()
                self._lineBuffer.append('&O' + "".join(numerals))
                self._pos += 3
            elif code == 0x0c:    # hex constant
                # signed, but that's not visible in hexa representation
                self._check_boundary(2)
                val = hex(self._data[self._pos + 2] << 8 | self._data[self._pos + 1]).replace('0x', '&H')
                self._lineBuffer.append(val.upper())
                self._pos += 3
            elif code == 0x0d:    # line pointer (unsigned)
                raise ValueError("line pointer (0x0d) shouldn't occur in saved program.")
            elif code == 0x0e:    # line number (unsigned)
                self._check_boundary(2)
                self._lineBuffer.append((self._data[self._pos + 2] << 8) | self._data[self._pos + 1])
                self._pos += 3
            elif code == 0x0f:    # one byte constant
                self._lineBuffer.append(self._data[self._pos + 1])
                self._pos += 2
            elif code == 0x10:    # Flags constant (unused)
                raise ValueError("unexpected 0x10 token")
            elif code >= 0x11 and code <= 0x1b:
                # Numbers from 0 to 10 have their own tokens
                self._lineBuffer.append(code - 0x11)
                self._pos += 1
            elif code == 0x1c:    # two byte integer constant (signed)
                self._check_boundary(2)
                val = ((self._data[self._pos + 2] & 0x7FFF) << 8) | self._data[self._pos + 1]
                if self._data[self._pos + 2] & 0x8000:
                    self._lineBuffer.append(-val)
                else:
                    self._lineBuffer.append(val)
                self._pos += 3
            elif code == 0x1d:    # four byte floating point constant
                self._check_boundary(4)
                self._lineBuffer.append(self._parse_float32(self._pos + 1))
                self._pos += 5
            elif code == 0x1e:    # unused
                raise ValueError("unexpected 0x1e token")
            elif code == 0x1f:    # eight byte double value
                self._check_boundary(8)
                self._lineBuffer.append(self._parse_float64(self._pos + 1))
                self._pos += 9
            elif code in tokens:
                # 1-byte tokens
                self._lineBuffer.append(tokens[code])
                self._pos += 1
            elif ((code << 8) | self._data[self._pos + 1]) in tokens:
                # 2-byte tokens
                # The boundary for that +1 is already checked at the beginning of the loop.
                self._lineBuffer.append(tokens[(code << 8) | self._data[self._pos + 1]])
                self._pos += 2
            else:
                raise ValueError("unexpected token: %d" % code)

        self._pos += 1    # consume the null byte

    def __str__(self):
        return "%5d %s" % (
            self._lineNum, ''.join([str(x) for x in self._lineBuffer]))


class GWBasic:
    """Class representing a gw-basic program"""

    def __init__(self, data: bytes, encoding: str):
        self._data = data
        self._encoding = encoding
        self._lines = []

        if data[0] != 0xff:
            raise ValueError("Expected 0xff as first character")

    def parse(self):
        # Parse the binary data line by line
        pos = 1
        
        # Don't test for the 0x1A ending here, because
        #   the line offset can start with that value.
        while pos < len(self._data) - 1:
            line = GWBasicLine(self._data, self._encoding, pos)
            line.parse()

            if line.isEOF:
                # Reached the end of the file
                break
            else:
                pos += line.get_consumed_byte_count()
                self._lines.append(line)

    def __str__(self):
        return "\n".join(str(line) for line in self._lines)
