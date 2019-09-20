# gwbasic-decoder

[GW-BASIC] (aka GWBASIC or Gee-Whiz Basic) was a BASIC interpreter developed by Microsoft and bundled with MS-DOS until the advent of [QBASIC] with MS-DOS 5.0. GW-BASIC stored programs in memory at a time when memory was very scarce. Hence it used a compact, binary representation of code. It used this same binary format for code saved on disk, which makes it hard to read GW-BASIC programs nowadays.

Or at least it used to. Thanks to [this site][tokens], I was able to write a decoder in Python. Run your `.BAS` file through the script (see below) and you'll get a human-readable version of the program back out. Enjoy!

## Example

    $ python convert.py GAME.BAS
     10 CLS
     20 SCREEN 8
     30 Y=320: X=100
     40 A$="": WHILE+ A$="":A$=INKEY$:WEND
     50 CIRCLE (Y,X),19,0
     55 IF M<>1 AND RND>.8 THEN GOSUB 160
     60 IF A$="2" THEN X=X+1
     70 IF A$="8" THEN X=X-1
     80 IF A$="4" THEN Y=Y-2
     90 IF A$="6" THEN Y=Y+2
    100 IF A$="7" THEN X=X-1: Y=Y-2
    110 IF A$="9" THEN X=X-1: Y=Y+2
    120 IF A$="3" THEN X=X+1: Y=Y+2
    130 IF A$="1" THEN X=X+1: Y=Y-2
    140 CIRCLE (Y,X),19
    143 FOR I=-18 TO 18
    145 IF POINT(Y,X+I)=-1 THEN END
    147 NEXT
    150 GOTO 40
    160 ON TIMER(1) GOSUB 200
    170 TIMER ON
    175 M=1: H=INT(1+RND*240)
    180 RETURN
    200 IF F=0 THEN R=12
    210 LINE(G,H)-(R,H),10
    220 F=1
    230 R=R+622
    240 IF R>640 THEN F=0: M=0: TIMER OFF
    250 RETURN

## Complete type support

The output is exactly the same as in the original GW-Basic.

    $ python convert.py TYPEDEMO.BAS
    10 ' Single precision floats (32 bit)
    20 A = 46.8: B = -1.09E-06: C = 3489!: D = 22.4822
    30 ' Double precision floats (64 bit)
    40 E# = 3.569D-39: F# = -.0001094327263526#: G# = 35#: H# = 78987654321.1234#
    50 ' String, Integer, Octal, Hexadecimal
    60 I$ = "Hello World!": J% = 1234: K = &O347: L = &H32F
    70 REM Tokenized types, one-byte type, more octal and hex
    80 PRINT 0; 1; 2; 3; 4; 5; 6; 7; 8; 9; 10; 63
    90 PRINT &O7234; &O1702; &O177777; &O0; &H3FB9; &HFFFF; &H0

## Custom code page for the extended ASCII characters

You can specify an encoding in an argument:

    $ python convert.py --encoding cp437 CODEPAGE.BAS
    10 ' IBM Code Page 437
    20 REM Årvíztürö tükörfúrógép
    30 PRINT "sin(α + ß) = sin(α)*cos(ß) + cos(α)*sin(ß)"

The most common code pages of the DOS era:
- cp437: The code page of the original IBM PC
- cp850: Latin-1 (Some symbols and Greek characters in the cp437 got replaced with more latin letters.)
- cp1252: Windows 1.0 -> Windows 98
- iso-8859-1: Western European encoding, early web standard

[gw-basic]: http://en.wikipedia.org/wiki/GW-BASIC
[qbasic]: http://en.wikipedia.org/wiki/QBASIC
[tokens]: http://www.chebucto.ns.ca/~af380/GW-BASIC-tokens.html
