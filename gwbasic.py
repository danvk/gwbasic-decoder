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
        self.lineBuffer = []
        self.isEOF = False
        self.pos = lineStart
    
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

    def GetConsumedByteCount(self) -> int:
        return self.pos - self.lineStart

    def CheckBoundary(self, required: int):
        if len(self.data) - self.pos - 1 < required:
            if self.lineNum > 0:
                raise Exception("Unexpected end of file after line %d" % self.lineNum)
            else:
                raise Exception("Unexpected end of file at byte position %s" % hex(self.pos))

    def Parse(self):
        """Forms a new line from the first line contained in the bytestream."""

        self.CheckBoundary(2)

        # first two bytes are address of next line. Mostly irrelevant, but if
        # they're both zero, this is the end of the program.
        if self.data[self.lineStart] == 0 and self.data[self.lineStart + 1] == 0:
            self.isEOF = True
            return
        
        self.pos += 2
        self.CheckBoundary(2)

        # next two bytes are the line number
        self.lineNum = (self.data[self.lineStart + 3] << 8) | self.data[self.lineStart + 2]
        self.pos += 2

        # States that show whether we are inside a REM (comment)
        # statement or inside quotes.
        insideRem = False
        insideQuotes = False

        self.CheckBoundary(1)

        while self.data[self.pos] != 0:
            self.CheckBoundary(1)
            code = self.data[self.pos]

            if code == 0x22 and not insideRem:  # Quote starts or ends
                # There was no quote escaping. You had to use CHR$() to
                #   output a quote character.
                insideQuotes = not insideQuotes
                self.lineBuffer.append('"')
                self.pos += 1
                continue
            elif code == 0x3a and not (insideQuotes or insideRem):
                if len(self.data) - self.pos > 2:
                    if self.data[self.pos + 1] == 0x8f and self.data[self.pos + 2] == 0xd9:
                        # REM block starts
                        # A single quote is an alias for a REM instruction
                        # It is stored with 3 bytes: 0x3a8fd9
                        insideRem = True    # a REM block never ends (inside a line)
                        self.lineBuffer.append("'")
                        self.pos += 3
                        continue

            if insideQuotes or insideRem or (code >= 0x20 and code <= 0x7e):
                # Decode the custom texts using the specified code page
                codeByte = code.to_bytes(1, byteorder='little', signed=False)
                self.lineBuffer.append(codeByte.decode(self.encoding))
                self.pos += 1
            elif code == 0x8f:     # REM block starts
                insideRem = True    # a REM block never ends (inside a line)
                self.lineBuffer.append('REM')
                self.pos += 1
            elif code == 0x0b:    # octal constant
                # signed, but that's not visible in octal representation
                self.CheckBoundary(2)

                val1 = str(((self.data[self.pos + 2] << 2) & 0x04) | (self.data[self.pos + 1] >> 6))
                if val1 == '0':
                    val1 = ''
                val2 = str((self.data[self.pos + 1] >> 3) & 0x07)
                if val1 == '' and val2 == '0':
                    val2 = ''
                val3 = str(self.data[self.pos + 1] & 0x07)
                
                self.lineBuffer.append('&O' + val1 + val2 + val3)
                self.pos += 3
            elif code == 0x0c:    # hex constant
                # signed, but that's not visible in hexa representation
                self.CheckBoundary(2)
                val = '&H' + hex(self.data[self.pos + 2] << 8 | self.data[self.pos + 1]).replace('0x', '')
                self.lineBuffer.append(val.upper())
                self.pos += 3
            elif code == 0x0d:    # line pointer (unsigned)
                raise ValueError("line pointer (0x0d) shouldn't occur in saved program.")
            elif code == 0x0e:    # line number (unsigned)
                self.CheckBoundary(2)
                self.lineBuffer.append((self.data[self.pos + 2] << 8) | self.data[self.pos + 1])
                self.pos += 3
            elif code == 0x0f:    # one byte constant
                self.lineBuffer.append(self.data[self.pos + 1])
                self.pos += 2
            elif code == 0x10:    # Flags constant (unused)
                raise ValueError("unexpected 0x10 token")
            elif code >= 0x11 and code <= 0x1b:
                # Numbers from 0 to 10 have their own tokens
                self.lineBuffer.append(code - 0x11)
                self.pos += 1
            elif code == 0x1c:    # two byte integer constant (signed)
                self.CheckBoundary(2)
                val = ((self.data[self.pos + 2] & 0x7FFF) << 8) | self.data[self.pos + 1]
                if self.data[self.pos + 2] & 0x8000:
                    self.lineBuffer.append(-val)
                else:
                    self.lineBuffer.append(val)
                self.pos += 3
            elif code == 0x1d:    # four byte floating point constant
                self.CheckBoundary(4)
                self.lineBuffer.append(self.ParseFloat32(self.pos + 1))
                self.pos += 5
            elif code == 0x1e:    # unused
                raise ValueError("unexpected 0x1e token")
            elif code == 0x1f:    # eight byte double value
                self.CheckBoundary(8)
                self.lineBuffer.append(self.ParseFloat64(self.pos + 1))
                self.pos += 9
            elif code in tokens:
                # 1-byte tokens
                self.lineBuffer.append(tokens[code])
                self.pos += 1
            elif ((code << 8) | self.data[self.pos + 1]) in tokens:
                # 2-byte tokens
                # The boundary for that +1 is already checked at the beginning of the loop.
                self.lineBuffer.append(tokens[(code << 8) | self.data[self.pos + 1]])
                self.pos += 2
            else:
                raise ValueError("unexpected token: %d" % code)

        self.pos += 1    # consume the null byte
        return

    def __str__(self):
        return "%5d %s" % (
            self.lineNum, ''.join([str(x) for x in self.lineBuffer]))


class gwBasic:
    """Class representing a gw-basic program"""

    def __init__(self, data: bytes, encoding: str):
        self.data = data
        self.encoding = encoding
        self.lines = []

        if data[0] != 0xff:
            raise ValueError("Expected 0xff as first character")

    def Parse(self):
        # Parse the binary data line by line
        pos = 1
        
        # Don't test for the 0x1A ending here, because
        #   the line offset can start with that value.
        while pos < len(self.data) - 1:
            line = gwBasicLine(self.data, self.encoding, pos)
            line.Parse()

            if line.isEOF:
                # Reached the end of the file
                break
            else:
                pos += line.GetConsumedByteCount()
                self.lines.append(line)

    def __str__(self):
        return "\n".join(str(line) for line in self.lines)
