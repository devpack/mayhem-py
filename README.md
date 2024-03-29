# mayhem-py

Python version of the classic Amiga game Mayhem, with support for online gaming (see bellow).

Try the HTML version (local gaming only) on: https://devpack.github.io/mayhem-html5 or https://devpack.itch.io/mayhem

----

Dependencies: pygame-ce, pygame-menu-ce, Twisted, Autobahn, msgpack, moderngl, numpy, imgui[pygame] (python3 -m pip install -r requirements.txt).

The game works with either pygame or pygame-ce (if you are using pygame, please use pygame-menu instead of pygame-menu-ce), currently it is tested against pygame-ce which has more features. 

Launch the game using pygame-menu to configure the options ("user_settings.dat" contains the saved options (note: you may need to remove this file between game updates)):

```
python3 mayhem.py
```

Keys 1 to 7 to change the map (online mode: only ship_1 can change the map). Two players on the keyboard and 2 on usb Gamepad/Joystick. Keyboard 1 = w (z), x, c, v, g ; Keyboard 2 = left, right, 0, ., enter

Run a GameServer (allow online gaming with friends):

```
python3 server.py
```

Local server url example: ws://127.0.0.1:4444

Room ID: any number (or str). 0 has a special meaning: find the first room where there is space left (or creates one if none found). Any room has a size of 4 players.

![Menu](https://github.com/devpack/mayhem-py/blob/main/assets/wiki/menu.png)

![Online_Game](https://github.com/devpack/mayhem-py/blob/main/assets/wiki/online_game.png)

TODO: Host a public facing GameServer.

Launch the game, local mode (Deprecated but still working):

```
python3 mayhem.py --width=1200 --height=800 --fps=60
```

Launch the game, online mode (Deprecated but still working):

```
python3 mayhem.py --player_name=tony --ship_control=k1 --server=ws://127.0.0.1:4444 -sap
python3 mayhem.py --player_name=tony --ship_control=k1 --server=ws://127.0.0.1:4444
python3 mayhem.py --player_name=tony --ship_control=k1 --server=ws://127.0.0.1:4444 -zoom
python3 mayhem.py --player_name=tony --ship_control=j1 --server=ws://127.0.0.1:4444 -sap
```

Some options to play with:

```
-sap : Show all players
-zoom : PyGame scaled mode, use full for 4K screens
-opengl : opengl backend (we render into a PyGame surface, then we convert this surface to a OpenGL texture and render it ; with that we can add fun effects playing with the shaders)
-show_options : GUI to change the game physics (OpenGL mode is mandatory for this option to work)
-ship_control : two keyboard layout, "k1" and "k2" ; "j1" for usb joystick
```

----

The original game by [Espen Skoglund](http://hol.abime.net/3853) was born in the early 90s on the Commodore Amiga. That was the great time of MC68000 Assembly.

![Mayhem game image](https://github.com/devpack/mayhem-py/blob/main/assets/wiki/mayhem_amiga.jpg)

[Video of the original Amiga game](https://www.youtube.com/watch?v=fs30DLGxqhs)

----

Around 2000 we made a [PC version](https://github.com/devpack/mayhem) of the game in C++.

It was then ported to [Raspberry Pi](https://www.raspberrypi.org/) by [Martin O'Hanlon](https://github.com/martinohanlon/mayhem-pi), even new gfx levels were added.

![Mayhem2](https://github.com/devpack/mayhem-py/blob/main/assets/wiki/mayhem2.jpg)

[Video - new level](https://youtu.be/E3mho6J6OG8)