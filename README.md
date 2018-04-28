# gwbasic-decoder

This repo contains Python code which lets you read your old GW-BASIC programs which are stored in binary `.BAS` format.

## Usage

    $ python convert.py GAME.BAS
    10 CLS
    20 SCREEN 8
    30 Y=320: X=100
    40 A$="": WHILE+ A$="":A$=INKEY$:WEND
    50 CIRCLE (Y,X),19,0
    55 IF M<>1 AND RND>0.800000011921 THEN GOSUB 160
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
