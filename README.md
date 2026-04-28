# SALETBot.py

```Welcome to my Wordle solver!
Hard mode? (Y/N): n

Candidates left: 2315

Pattern for 'crane': salet _g___

Candidates left: 82
Theoretical Analysis of Top 100...
Progress: 100%

WORD    | WIN % | EXP   | WORST | 5+ CT | STATS [1,2,3,4,5,6,X]
--------|-------|-------|-------|-------|-----------------------
CORNY   | 100.0 | 3.573 | 5     | 1     | [0, 0, 36, 45, 1, 0, 0]
CRONY   | 100.0 | 3.598 | 5     | 1     | [0, 0, 34, 47, 1, 0, 0]
CORNI   | 100.0 | 3.634 | 5     | 2     | [0, 0, 32, 48, 2, 0, 0]
CURNY   | 100.0 | 3.659 | 5     | 2     | [0, 0, 30, 50, 2, 0, 0]
CARNY   | 100.0 | 3.683 | 5     | 2     | [0, 0, 28, 52, 2, 0, 0]
DORMY   | 100.0 | 3.683 | 5     | 2     | [0, 0, 28, 52, 2, 0, 0]
GYRON   | 100.0 | 3.683 | 5     | 2     | [0, 0, 28, 52, 2, 0, 0]
MINOR   | 100.0 | 3.683 | 5     | 2     | [0, 0, 28, 52, 2, 0, 0]
...

Pattern for 'corny':```

(note you may (highly recommended) to change the word lists to filter swear words or slurs for a family-friendly clone or version.)

* This is a simple Wordle solver which is assisted with Gemini.
* Before running the code, make sure that you have already set up the word lists, proper word list and the Python compiler. (PyCharm is highly recommended)
* If there are no problems, you can run the code. It will manually ask the starting word and te hard mode function. Type "Y" for hard mode and "N" for easy mode.
* For the typing of the colourings, use "g" for green, "y" for yellow and "_" (underscore) for grey along with the starting word. Type like "salet _g___".
* EXP means the average guesses left of the remaining words, win % means the winning rate (the puzzles which can be solved within 6 guesses), worst means the worst case, 5+ CT means the words solved in 5 guesses or more (lower is better).
* This Wordle solver can solve every Wordle puzzle within 5 guesses and with an average of 3.421 guesses.
