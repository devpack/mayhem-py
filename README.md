# mayhem-py

Python version of the classic Amiga game Mayhem. Added support for online gaming (see server.py).

Try the HTML version on: https://devpack.github.io/mayhem-html5 or https://devpack.itch.io/mayhem

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

Dependencies: PyGame, Twisted, Autobahn, msgpack (python3 -m pip install -r requirements.txt)

Launch the game (local mode):

```
python3 mayhem.py --width=1200 --height=800 --fps=60
```

Launch the game (online mode):

```
python3 mayhem.py --player_name=tony --ship_control=k1 --server=ws://127.0.0.1:4444 -sap
python3 mayhem.py --player_name=tony --ship_control=k1 --server=ws://127.0.0.1:4444
python3 mayhem.py --player_name=tony --ship_control=k1 --server=ws://127.0.0.1:4444 -zoom
python3 mayhem.py --player_name=tony --ship_control=j1 --server=ws://127.0.0.1:4444 -sap
```

Keys 1 to 7 to change the map (online mode, only ship_1 can change the map). Two players on the keyboard and 2 on usb Gamepad/Joystick.
