# gwbasic-decoder

[GW-BASIC] (aka GWBASIC or Gee-Whiz Basic) was a BASIC interpreter developed by Microsoft and bundled with MS-DOS until the advent of [QBASIC] with MS-DOS 5.0. GW-BASIC stored programs in memory at a time when memory was very scarce. Hence it used a compact, binary representation of code. It used this same binary format for code saved on disk, which makes it hard to read GW-BASIC programs nowadays.

Or at least it used to. Thanks to [this site][tokens], I was able to write a decoder in Python. Run your `.BAS` file through the script (see below) and you'll get a human-readable version of the program back out. Enjoy!

## Simple example

    $ python convert.py GAME.BAS
     10 CLS
     20 SCREEN 8
     30 Y=320: X=100
     40 A$="": WHILE+ A$="":A$=INKEY$:WEND
     50 CIRCLE (Y,X),19,0
     55 IF M<>1 AND RND>0.8 THEN GOSUB 160
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

[gw-basic]: http://en.wikipedia.org/wiki/GW-BASIC
[qbasic]: http://en.wikipedia.org/wiki/QBASIC
[tokens]: http://www.chebucto.ns.ca/~af380/GW-BASIC-tokens.html
