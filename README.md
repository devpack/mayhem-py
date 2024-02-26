# mayhem-py

Python version of the classic Amiga game Mayhem.

Try the HTML version on: https://devpack.github.io/mayhem-html5

----

The original game by [Espen Skoglund](http://hol.abime.net/3853) was born in the early 90s on the Commodore Amiga. That was the great time of MC68000 Assembly.

![Mayhem game image](https://github.com/devpack/mayhem-py/blob/main/assets/wiki/mayhem_amiga.jpg)

[Video of the original Amiga game](https://www.youtube.com/watch?v=fs30DLGxqhs)

----

Around 2000 we made a [PC version](https://github.com/devpack/mayhem) of the game in C++.

It was then ported to [Raspberry Pi](https://www.raspberrypi.org/) by [Martin O'Hanlon](https://github.com/martinohanlon/mayhem-pi), even new gfx levels were added.

![Mayhem2](https://github.com/devpack/mayhem-py/blob/main/assets/wiki/mayhem2.jpg)

[Video - new level](https://youtu.be/E3mho6J6OG8)

----

The only dependency to install should be PyGame (python3 -m pip install pygame)

Launch the game:

```
python3 mayhem.py --width=1200 --height=800 --nb_player=4 --fps=60
```

Keys 1 to 7 to change the map. Two players on the keyboard and 2 on usb Gamepad/Joystick.
