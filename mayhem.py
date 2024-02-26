# -*- coding: utf-8 -*-
"""
Python version of the great Mayhem Amiga game. The original by Espen Skoglund (http://hol.abime.net/3853) was born in the early 90s on the Commodore Amiga. That was the great time of MC68000 Assembly.

Around 2000 we made a PC version (https://github.com/devpack/mayhem) of the game in C++.

It was then ported to Raspberry Pi by Martin O'Hanlon (https://github.com/martinohanlon/mayhem-pi).

Anthony Prieur
anthony.prieur@gmail.com
"""

"""
Usage example:

python3 mayhem.py --width=1500 --height=900 --nb_player=4

python3 mayhem.py --motion=gravity
python3 mayhem.py --motion=thrust
python3 mayhem.py -r=played1.dat --motion=gravity
python3 mayhem.py -pr=played1.dat --motion=gravity
"""

import os, sys, argparse, random, math, time, pickle
from random import randint

import pygame
from pygame import gfxdraw
from pygame.locals import *

# -------------------------------------------------------------------------------------------------
# General

DEBUG_TEXT_XPOS = 0

WHITE    = (255, 255, 255)
RED      = (255, 0, 0)
LVIOLET  = (128, 0, 128)

USE_MINI_MASK = True # mask the size of the ship (instead of the player view size)

# -------------------------------------------------------------------------------------------------
# SHIP dynamics

SLOW_DOWN_COEF = 1.7 # somehow the C++ version is slower with the same physics coef ?

SHIP_MASS = 1.0
SHIP_THRUST_MAX = 0.3 / SLOW_DOWN_COEF
SHIP_ANGLESTEP = 5
SHIP_ANGLE_LAND = 30
SHIP_MAX_LIVES = 100
SHIP_SPRITE_SIZE = 32

iG       = 0.08 / SLOW_DOWN_COEF
iXfrott  = 0.984
iYfrott  = 0.99
iCoeffax = 0.6
iCoeffay = 0.6
iCoeffvx = 0.6
iCoeffvy = 0.6
iCoeffimpact = 0.02
MAX_SHOOT = 20

# -------------------------------------------------------------------------------------------------
# Levels / controls

CURRENT_LEVEL = 1

SHIP_1_KEYS = {"left":pygame.K_LEFT, "right":pygame.K_RIGHT, "up":pygame.K_UP, "down":pygame.K_DOWN, \
               "thrust":pygame.K_KP_PERIOD, "shoot":pygame.K_KP_ENTER, "shield":pygame.K_KP0}
SHIP_1_JOY  = 0 # 0 means no joystick, =!0 means joystck number SHIP_1_JOY - 1

SHIP_2_KEYS = {"left":pygame.K_w, "right":pygame.K_x, "up":pygame.K_UP, "down":pygame.K_DOWN, \
               "thrust":pygame.K_v, "shoot":pygame.K_g, "shield":pygame.K_c}
SHIP_2_JOY  = 1 # 0 means no joystick, =!0 means joystck number SHIP_1_JOY - 1

SHIP_3_KEYS = {"left":pygame.K_w, "right":pygame.K_x, "up":pygame.K_UP, "down":pygame.K_DOWN, \
               "thrust":pygame.K_v, "shoot":pygame.K_g, "shield":pygame.K_c}
SHIP_3_JOY  = 2 # 0 means no joystick, =!0 means joystck number SHIP_1_JOY - 1

SHIP_4_KEYS = {"left":pygame.K_w, "right":pygame.K_x, "up":pygame.K_UP, "down":pygame.K_DOWN, \
               "thrust":pygame.K_v, "shoot":pygame.K_g, "shield":pygame.K_c}
SHIP_4_JOY  = 0 # 0 means no joystick, =!0 means joystck number SHIP_1_JOY - 1

# -------------------------------------------------------------------------------------------------
# Assets

MAP_1 = os.path.join("assets", "level1", "Mayhem_Level1_Map_256c.bmp")
MAP_2 = os.path.join("assets", "level2", "Mayhem_Level2_Map_256c.bmp")
MAP_3 = os.path.join("assets", "level3", "Mayhem_Level3_Map_256c.bmp")
MAP_4 = os.path.join("assets", "level4", "Mayhem_Level4_Map_256c.bmp")
MAP_5 = os.path.join("assets", "level5", "Mayhem_Level5_Map_256c.bmp")
MAP_6 = os.path.join("assets", "level6", "mayhem_big_holes.bmp")
MAP_7 = os.path.join("assets", "level7", "mayhem_big2_holes1.bmp")

SOUND_THURST  = os.path.join("assets", "default", "sfx_loop_thrust.wav")
SOUND_EXPLOD  = os.path.join("assets", "default", "sfx_boom.wav")
SOUND_BOUNCE  = os.path.join("assets", "default", "sfx_rebound.wav")
SOUND_SHOOT   = os.path.join("assets", "default", "sfx_shoot.wav")
SOUND_SHIELD  = os.path.join("assets", "default", "sfx_loop_shield.wav")

SHIP_1_PIC        = os.path.join("assets", "default", "ship1_256c.bmp")
SHIP_1_PIC_THRUST = os.path.join("assets", "default", "ship1_thrust_256c.bmp")
SHIP_1_PIC_SHIELD = os.path.join("assets", "default", "ship1_shield_256c.bmp")

SHIP_2_PIC        = os.path.join("assets", "default", "ship2_256c.bmp")
SHIP_2_PIC_THRUST = os.path.join("assets", "default", "ship2_thrust_256c.bmp")
SHIP_2_PIC_SHIELD = os.path.join("assets", "default", "ship2_shield_256c.bmp")

SHIP_3_PIC        = os.path.join("assets", "default", "ship3_256c.bmp")
SHIP_3_PIC_THRUST = os.path.join("assets", "default", "ship3_thrust_256c.bmp")
SHIP_3_PIC_SHIELD = os.path.join("assets", "default", "ship3_shield_256c.bmp")

SHIP_4_PIC        = os.path.join("assets", "default", "ship4_256c.bmp")
SHIP_4_PIC_THRUST = os.path.join("assets", "default", "ship4_thrust_256c.bmp")
SHIP_4_PIC_SHIELD = os.path.join("assets", "default", "ship4_shield_256c.bmp")

# -------------------------------------------------------------------------------------------------

class Debris():
    def __init__(self):
        self.x = 0
        self.y = 0
        self.xposprecise = 0
        self.yposprecise = 0
        self.ax = 0
        self.ay = 0
        self.vx = 0
        self.vy = 0
        self.impultion = 0
        self.angle = 0

# -------------------------------------------------------------------------------------------------

class Shot():
    def __init__(self):
        self.x = 0
        self.y = 0
        self.xposprecise = 0
        self.yposprecise = 0
        self.dx = 0
        self.dy = 0

# -------------------------------------------------------------------------------------------------

class Ship():

    def __init__(self, screen_width, screen_height, ship_number, nb_player, xpos, ypos, ship_pic, ship_pic_thrust, ship_pic_shield, keys_mapping, joystick_number, lives):

        margin_size = 0
        w_percent = 1.0
        h_percent = 1.0

        self.view_width  = int((screen_width * w_percent) / 2)
        self.view_height = int((screen_height * h_percent) / 2)

        if ship_number == 1:
            self.view_left = margin_size
            self.view_top = margin_size

        elif ship_number == 2:
            self.view_left = margin_size + self.view_width + margin_size
            self.view_top = margin_size

        elif ship_number == 3:
            self.view_left = margin_size
            self.view_top = margin_size + self.view_height + margin_size

        elif ship_number == 4:
            self.view_left = margin_size + self.view_width + margin_size
            self.view_top = margin_size + self.view_height + margin_size

        self.init_xpos = xpos
        self.init_ypos = ypos
        
        self.xpos = xpos
        self.ypos = ypos
        self.xposprecise = xpos
        self.yposprecise = ypos

        self.vx = 0.0
        self.vy = 0.0
        self.ax = 0.0
        self.ay = 0.0

        self.impactx = 0.0
        self.impacty = 0.0

        self.angle  = 0.0
        self.thrust = 0.0
        self.shield = False
        self.shoot  = False
        self.shoot_delay = False
        self.landed = False
        self.bounce = False
        self.shots = []
        self.lives = lives
        
        self.explod = False
        self.explod_tick = 0
        self.debris = []

        # sound
        self.sound_thrust = pygame.mixer.Sound(SOUND_THURST)
        self.sound_explod = pygame.mixer.Sound(SOUND_EXPLOD)
        self.sound_bounce = pygame.mixer.Sound(SOUND_BOUNCE)
        self.sound_shoot  = pygame.mixer.Sound(SOUND_SHOOT)
        self.sound_shield = pygame.mixer.Sound(SOUND_SHIELD)

        # controls
        self.thrust_pressed = False
        self.left_pressed   = False
        self.right_pressed  = False
        self.shoot_pressed  = False
        self.shield_pressed = False

        # ship pic: 32x32, black (0,0,0) background, no alpha
        self.ship_pic = pygame.image.load(ship_pic).convert()
        self.ship_pic.set_colorkey( (0, 0, 0) ) # used for the mask, black = background, not the ship
        self.ship_pic_thrust = pygame.image.load(ship_pic_thrust).convert()
        self.ship_pic_thrust.set_colorkey( (0, 0, 0) ) # used for the mask, black = background, not the ship
        self.ship_pic_shield = pygame.image.load(ship_pic_shield).convert()
        self.ship_pic_shield.set_colorkey( (0, 0, 0) ) # used for the mask, black = background, not the ship

        self.image = self.ship_pic
        self.mask = pygame.mask.from_surface(self.image)

        self.keys_mapping = keys_mapping
        self.joystick_number = joystick_number

    def reset(self):
        self.xpos = self.init_xpos
        self.ypos = self.init_ypos

        self.xposprecise = self.xpos
        self.yposprecise = self.ypos

        self.vx = 0.0
        self.vy = 0.0
        self.ax = 0.0
        self.ay = 0.0

        self.impactx = 0.0
        self.impacty = 0.0

        self.angle  = 0.0
        self.thrust = 0.0
        self.shield = False
        self.shoot  = False
        self.shoot_delay = False
        self.landed = False
        self.bounce = False
        self.explod = False
        self.explod_tick = 0
        self.debris = []

        self.lives -= 1

    def init_debris(self):

        for i in range(8):
            self.debris.append(Debris())

        deb_angle = 22

        for deb in self.debris:
            deb.angle = deb_angle
            deb.x = (self.xpos + 15) + 20 * -math.cos(math.radians(90 - deb.angle))
            deb.y = (self.ypos + 16) + 20 * -math.sin(math.radians(90 - deb.angle))
            deb.xposprecise = deb.x
            deb.yposprecise = deb.y
            deb.ax = 0
            deb.ay = 0
            deb.impultion = 8
            deb.vx = 0
            deb.vy = 0

            deb_angle += 45

    def explod_sequence(self, env):

        if self.explod:
            self.sound_thrust.stop()
            self.sound_shoot.stop()
            self.sound_shield.stop()
            self.sound_bounce.stop()

            if self.explod_tick == 0:
                self.sound_explod.play()
                self.init_debris()
            else:
                # TODO draw explosion
                for deb in self.debris:

                    # move debris
                    deb.ax = deb.impultion * -math.cos(math.radians(90 - deb.angle))
                    deb.ay = iG*5 + (deb.impultion * -math.sin(math.radians(90 - deb.angle)))

                    deb.vx = deb.vx + (iCoeffax * deb.ax)
                    deb.vy = deb.vy + (iCoeffay * deb.ay)

                    deb.vx = deb.vx * iXfrott
                    deb.vy = deb.vy * iYfrott

                    deb.vx = deb.vx
                    deb.vy = deb.vy

                    deb.xposprecise = deb.xposprecise + (iCoeffvx * deb.vx)
                    deb.yposprecise = deb.yposprecise + (iCoeffvy * deb.vy)

                    deb.impultion = 0

                    # plot debris
                    deb.x = int(deb.xposprecise)
                    deb.y = int(deb.yposprecise)             
                    
                    try:
                        c = env.map_buffer.get_at((int(deb.x), int(deb.y)))
                        if (c.r != 0) or (c.g != 0) or (c.b != 0):
                            self.debris.remove(deb)

                        gfxdraw.pixel(env.map_buffer, int(deb.x) , int(deb.y), WHITE)
                        #pygame.draw.circle(env.map_buffer, WHITE, (int(deb.x) , int(deb.y)), 1)

                    # out of surface
                    except IndexError:
                        self.debris.remove(deb)

            # explosion time
            self.explod_tick +=1

            if self.explod_tick > env.max_fps * 2:
                self.reset()
    
    def update(self, env, left_pressed, right_pressed, thrust_pressed, shoot_pressed, shield_pressed):

        if self.explod:
            return
        
        # normal play
        if not env.play_recorded:

            # record play ?
            if env.record_play:
                env.played_data.append((left_pressed, right_pressed, thrust_pressed, shield_pressed, shoot_pressed))

        # play recorded
        else:
            try:
                data_i = env.played_data[env.frames]

                left_pressed   = True if data_i[0] else False
                right_pressed  = True if data_i[1] else False
                thrust_pressed = True if data_i[2] else False
                shield_pressed = True if data_i[3] else False
                shoot_pressed  = True if data_i[4] else False

            except:
                print("End of playback")
                print("Frames=", env.frames)
                print("%s seconds" % int(env.frames/env.max_fps))
                sys.exit(0)


        self.do_move(env, left_pressed, right_pressed, thrust_pressed, shoot_pressed, shield_pressed)

    def do_move(self, env, left_pressed, right_pressed, thrust_pressed, shoot_pressed, shield_pressed):

        if env.motion == "thrust":

            # pic
            if thrust_pressed:
                self.image = self.ship_pic_thrust
            else:
                self.image = self.ship_pic

            # angle
            if left_pressed:
                self.angle += SHIP_ANGLESTEP
            if right_pressed:
                self.angle -= SHIP_ANGLESTEP

            self.angle = self.angle % 360

            if thrust_pressed:
                coef = 2
                self.xposprecise -= coef * math.cos( math.radians(90 - self.angle) )
                self.yposprecise -= coef * math.sin( math.radians(90 - self.angle) )
                
                # transfer to screen coordinates
                self.xpos = int(self.xposprecise)
                self.ypos = int(self.yposprecise)

        elif env.motion == "gravity":
    
            self.image = self.ship_pic
            self.thrust = 0.0
            self.shield = False

            # shield
            if shield_pressed:
                self.image = self.ship_pic_shield
                self.shield = True
                self.sound_thrust.stop()

                if not pygame.mixer.get_busy():
                    self.sound_shield.play(-1)
            else:
                self.shield = False
                self.sound_shield.stop()

                # thrust
                if thrust_pressed:
                    self.image = self.ship_pic_thrust

                    #self.thrust += 0.1
                    #if self.thrust >= SHIP_THRUST_MAX:
                    self.thrust = SHIP_THRUST_MAX

                    if not pygame.mixer.get_busy():
                        self.sound_thrust.play(-1)

                    self.landed = False

                else:
                    self.thrust = 0.0
                    self.sound_thrust.stop()

            # shoot delay
            if shoot_pressed and not self.shoot:
                self.shoot_delay = True
            else:
                self.shoot_delay = False

            # shoot
            if shoot_pressed:
                self.shoot = True

                if self.shoot_delay:
                    if len(self.shots) < MAX_SHOOT:
                        if not pygame.mixer.get_busy():
                            self.sound_shoot.play()

                        self.add_shots()
            else:
                self.shoot = False
                self.sound_shoot.stop()

            #
            self.bounce = False

            if not self.landed:
                # angle
                if left_pressed:
                    self.angle += SHIP_ANGLESTEP
                if right_pressed:
                    self.angle -= SHIP_ANGLESTEP

                # 
                self.angle = self.angle % 360

                # https://gafferongames.com/post/integration_basics/
                self.ax = self.thrust * -math.cos( math.radians(90 - self.angle) ) # ax = thrust * sin1
                self.ay = iG + (self.thrust * -math.sin( math.radians(90 - self.angle))) # ay = g + thrust * (-cos1)

                # shoot when shield is on
                if self.impactx or self.impacty:
                    self.ax += iCoeffimpact * self.impactx
                    self.ay += iCoeffimpact * self.impacty
                    self.impactx = 0.
                    self.impacty = 0.

                self.vx = self.vx + (iCoeffax * self.ax) # vx += coeffa * ax
                self.vy = self.vy + (iCoeffay * self.ay) # vy += coeffa * ay

                self.vx = self.vx * iXfrott # on freine de xfrott
                self.vy = self.vy * iYfrott # on freine de yfrott

                self.xposprecise = self.xposprecise + (iCoeffvx * self.vx) # xpos += coeffv * vx
                self.yposprecise = self.yposprecise + (iCoeffvy * self.vy) # ypos += coeffv * vy

            else:
                self.vx = 0.
                self.vy = 0.
                self.ax = 0.
                self.ay = 0.

            # transfer to screen coordinates
            self.xpos = int(self.xposprecise)
            self.ypos = int(self.yposprecise)

            # wrap zone 1
            if env.level == 1:
                if self.ypos <= 160 and self.xpos >= 174 and self.xpos <= 184:
                    self.xpos = 344
                    self.ypos = 1052
                    self.xposprecise = self.xpos
                    self.yposprecise = self.ypos
                  
                if 1053 <= self.ypos and self.xpos >= 339 and self.xpos <= 349:
                    self.xpos = 179
                    self.ypos = 165
                    self.xposprecise = self.xpos
                    self.yposprecise = self.ypos

            # wrap horizontally / vertically
            if self.xpos > env.MAP_WIDTH:
                self.xpos = 0
                self.xposprecise = self.xpos
            elif self.xpos < 0:
                self.xpos = env.MAP_WIDTH
                self.xposprecise = self.xpos
            # H
            if self.ypos > env.MAP_HEIGHT:
                self.ypos = 0
                self.yposprecise = self.ypos
            elif self.ypos < 0:
                self.ypos = env.MAP_HEIGHT
                self.yposprecise = self.ypos

            # landed ?
            self.is_landed(env)

        #
        # rotate
        self.image_rotated = pygame.transform.rotate(self.image, self.angle)
        self.mask = pygame.mask.from_surface(self.image_rotated)

        rect = self.image_rotated.get_rect()
        self.rot_xoffset = int( ((SHIP_SPRITE_SIZE - rect.width)/2) )  # used in draw() and collide_map()
        self.rot_yoffset = int( ((SHIP_SPRITE_SIZE - rect.height)/2) ) # used in draw() and collide_map()

    def plot_shots(self, map_buffer):
        for shot in list(self.shots): # copy of self.shots
            shot.xposprecise += shot.dx
            shot.yposprecise += shot.dy
            shot.x = int(shot.xposprecise)
            shot.y = int(shot.yposprecise)

            try:
                c = map_buffer.get_at((int(shot.x), int(shot.y)))
                if (c.r != 0) or (c.g != 0) or (c.b != 0):
                    self.shots.remove(shot)

                gfxdraw.pixel(map_buffer, int(shot.x) , int(shot.y), WHITE)
                #pygame.draw.circle(map_buffer, WHITE, (int(shot.x) , int(shot.y)), 1)
                #pygame.draw.line(map_buffer, WHITE, (int(self.xpos + SHIP_SPRITE_SIZE/2), int(self.ypos + SHIP_SPRITE_SIZE/2)), (int(shot.x), int(shot.y)))

            # out of surface
            except IndexError:
                self.shots.remove(shot)

        if 0:
            for i in range(len(self.shots)):
                try:
                    shot1 = self.shots[i]
                    shot2 = self.shots[i+1]
                    pygame.draw.line(map_buffer, WHITE, (int(shot1.x), int(shot1.y)), (int(shot2.x), int(shot2.y)))
                except IndexError:
                    pass

    def add_shots(self):
        shot = Shot()

        shot.x = (self.xpos+15) + 18 * -math.cos(math.radians(90 - self.angle))
        shot.y = (self.ypos+16) + 18 * -math.sin(math.radians(90 - self.angle))
        shot.xposprecise = shot.x
        shot.yposprecise = shot.y
        shot.dx = 5.1 * -math.cos(math.radians(90 - self.angle))
        shot.dy = 5.1 * -math.sin(math.radians(90 - self.angle))
        shot.dx += self.vx / 3.5
        shot.dy += self.vy / 3.5

        self.shots.append(shot)

    def is_landed(self, env):

        for plaform in env.platforms:
            xmin  = plaform[0] - (SHIP_SPRITE_SIZE - 23)
            xmax  = plaform[1] - (SHIP_SPRITE_SIZE - 9)
            yflat = plaform[2] - (SHIP_SPRITE_SIZE - 2)

            #print(self.ypos, yflat)

            if ((xmin <= self.xpos) and (self.xpos <= xmax) and
               ((self.ypos == yflat) or ((self.ypos-1) == yflat) or ((self.ypos-2) == yflat) or ((self.ypos-3) == yflat) ) and
               (self.vy > 0) and (self.angle<=SHIP_ANGLE_LAND or self.angle>=(360-SHIP_ANGLE_LAND)) ):

                self.vy = - self.vy / 1.2
                self.vx = self.vx / 1.1
                self.angle = 0
                self.ypos = yflat
                self.yposprecise = yflat

                if ( (-1.0/SLOW_DOWN_COEF <= self.vx) and (self.vx < 1.0/SLOW_DOWN_COEF) and (-1.0/SLOW_DOWN_COEF < self.vy) and (self.vy < 1.0/SLOW_DOWN_COEF) ):
                    self.landed = True
                    self.bounce = False
                else:
                    self.bounce = True
                    self.sound_bounce.play()

                return True

        return False

    def do_test_collision(self, platforms):
        test_it = True

        for plaform in platforms:
            xmin  = plaform[0] - (SHIP_SPRITE_SIZE - 23)
            xmax  = plaform[1] - (SHIP_SPRITE_SIZE - 9)
            yflat = plaform[2] - (SHIP_SPRITE_SIZE - 2)

            #if ((xmin<=self.xpos) and (self.xpos<=xmax) and ((self.ypos==yflat) or ((self.ypos-1)==yflat) or ((self.ypos-2)==yflat) or ((self.ypos-3)==yflat))  and  (self.angle<=SHIP_ANGLE_LAND or self.angle>=(360-SHIP_ANGLE_LAND)) ):
            #    test_it = False
            #    break
            if (self.shield and (xmin<=self.xpos) and (self.xpos<=xmax) and ((self.ypos==yflat) or ((self.ypos-1)==yflat) or ((self.ypos-2)==yflat) or ((self.ypos-3)==yflat) or ((self.ypos+1)==yflat)) and  (self.angle<=SHIP_ANGLE_LAND or self.angle>=(360-SHIP_ANGLE_LAND)) ):
                test_it = False
                break
            if ((self.thrust) and (xmin<=self.xpos) and (self.xpos<=xmax) and ((self.ypos==yflat) or ((self.ypos-1)==yflat) or ((self.ypos+1)==yflat) )):
                test_it = False
                break

        return test_it

    def draw(self, map_buffer):

        if self.explod:
            return
        
        #game_window.blit(self.image_rotated, (self.view_width/2 + self.view_left + self.rot_xoffset, self.view_height/2 + self.view_top + self.rot_yoffset))
        map_buffer.blit(self.image_rotated, (self.xpos + self.rot_xoffset, self.ypos + self.rot_yoffset))

    def collide_map(self, map_buffer, map_buffer_mask, platforms):

        if self.explod:
            return
        
        # ship size mask
        if USE_MINI_MASK:
            mini_area = Rect(self.xpos, self.ypos, SHIP_SPRITE_SIZE, SHIP_SPRITE_SIZE)
            try:
                mini_subsurface = map_buffer.subsurface(mini_area)
            except ValueError:
                # wrap W or H
                return
            
            mini_subsurface.set_colorkey( (0, 0, 0) ) # used for the mask, black = background
            mini_mask = pygame.mask.from_surface(mini_subsurface)

            if self.do_test_collision(platforms):
                offset = (self.rot_xoffset, self.rot_yoffset) # pos of the ship

                if mini_mask.overlap(self.mask, offset): # https://stackoverflow.com/questions/55817422/collision-between-masks-in-pygame/55818093#55818093
                    self.explod = True

        # player view size mask
        else:
            if self.do_test_collision(platforms):
                offset = (self.xpos + self.rot_xoffset, self.ypos + self.rot_yoffset) # pos of the ship

                if map_buffer_mask.overlap(self.mask, offset): # https://stackoverflow.com/questions/55817422/collision-between-masks-in-pygame/55818093#55818093
                    self.explod = True

    def collide_ship(self, ships):
        
        if self.explod:
            return

        for ship in ships:
            if self != ship:
                offset = ((ship.xpos - self.xpos), (ship.ypos - self.ypos))
                if self.mask.overlap(ship.mask, offset):
                    self.explod = True
                    ship.explod = True

    def collide_shots(self, ships):

        for ship in ships:

            if self != ship:
                for shot in self.shots:
                    try:
                        if ship.mask.get_at((shot.x - ship.xpos, shot.y - ship.ypos)):
                            if not ship.shield:
                                ship.explod = True
                                return
                            else:
                                ship.impactx = shot.dx
                                ship.impacty = shot.dy
                    # out of ship mask => no collision
                    except IndexError:
                        pass

                for deb in self.debris:
                    try:
                        if ship.mask.get_at((deb.x - ship.xpos, deb.y - ship.ypos)):
                            if not ship.shield:
                                ship.explod = True
                                return
                            else:
                                ship.impactx = deb.dx
                                ship.impacty = deb.dy
                    # out of ship mask => no collision
                    except IndexError:
                        pass

# -------------------------------------------------------------------------------------------------

class MayhemEnv():
    
    def __init__(self, game, level=1, max_fps=60, debug_print=1, nb_player=2, motion="gravity", record_play="", play_recorded=""):

        self.myfont = pygame.font.SysFont('Arial', 20)

        self.nb_player = nb_player

        # screen
        self.game = game
        self.game.window.fill((0, 0, 0))
        self.level = level
        #self.level = randint(1, 5)
        self.motion = motion
        self.debug_print = debug_print
        self.max_fps = max_fps

        # record / play recorded
        self.record_play = record_play
        self.played_data = [] # [(0,0,0), (0,0,1), ...] (left, right, thrust)

        self.play_recorded = play_recorded

        if self.play_recorded:
            with open(self.play_recorded, "rb") as f:
                self.played_data = pickle.load(f)

        # FPS
        self.clock = pygame.time.Clock()
        self.paused = False
        self.frames = 0

        # per level data
        self.map = self.game.getv("map", current_level=self.level)
        self.map_buffer = self.game.getv("map_buffer", current_level=self.level)
        self.map_buffer_mask = self.game.getv("map_buffer_mask", current_level=self.level)
        self.platforms = self.game.getv("platforms", current_level=self.level)

        self.set_level(level)

    def main_loop(self):

        while True:

            self.game_loop()

            for ship in self.ships:
                ship.sound_thrust.stop()
                ship.sound_bounce.stop()
                ship.sound_shield.stop()
                ship.sound_shoot.stop()
                ship.sound_explod.play()

            # record play ?
            self.record_it()

    def record_it(self):

        if self.record_play:
            with open(self.record_play, "wb") as f:
                pickle.dump(self.played_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            time.sleep(0.1)
            print("Frames=", self.frames)
            print("%s seconds" % int(self.frames/self.max_fps))
            sys.exit(0)

    def ship_key_down(self, key, ship, key_mapping):

        if key == key_mapping["left"]:
            ship.left_pressed = True
        if key == key_mapping["right"]:
            ship.right_pressed = True
        if key == key_mapping["thrust"]:
            ship.thrust_pressed = True
        if key == key_mapping["shoot"]:
            ship.shoot_pressed = True
        if key == key_mapping["shield"]:
            ship.shield_pressed = True

    def ship_key_up(self, key, ship, key_mapping):

        if key == key_mapping["left"]:
            ship.left_pressed = False
        if key == key_mapping["right"]:
            ship.right_pressed = False
        if key == key_mapping["thrust"]:
            ship.thrust_pressed = False
        if key == key_mapping["shoot"]:
            ship.shoot_pressed = False
        if key == key_mapping["shield"]:
            ship.shield_pressed = False
            
    def set_level(self, level_nb):
        self.level = level_nb

        self.MAP_WIDTH  = 792
        self.MAP_HEIGHT = 1200

        if self.level == 6:
            self.MAP_WIDTH *= 2
            self.MAP_HEIGHT *= 2
        elif self.level == 7:
            self.MAP_WIDTH *= 2
            self.MAP_HEIGHT *= 3

        self.platforms = self.game.getv("platforms", current_level=self.level)

        SHIP1_X = (self.platforms[0][0] + self.platforms[0][1])/2 - 16
        SHIP1_Y = self.platforms[0][2] -29
        SHIP2_X = (self.platforms[1][0] + self.platforms[1][1])/2 - 16
        SHIP2_Y = self.platforms[1][2] -29
        SHIP3_X = (self.platforms[2][0] + self.platforms[2][1])/2 - 16
        SHIP3_Y = self.platforms[2][2] -29
        SHIP4_X = (self.platforms[3][0] + self.platforms[3][1])/2 - 16
        SHIP4_Y = self.platforms[3][2] -29

        self.ships = []

        self.ship_1 = Ship(self.game.screen_width, self.game.screen_height, 1, self.nb_player, SHIP1_X, SHIP1_Y, \
                                SHIP_1_PIC, SHIP_1_PIC_THRUST, SHIP_1_PIC_SHIELD, SHIP_1_KEYS, SHIP_1_JOY, SHIP_MAX_LIVES)

        self.ship_2 = Ship(self.game.screen_width, self.game.screen_height, 2, self.nb_player, SHIP2_X, SHIP2_Y, \
                            SHIP_2_PIC, SHIP_2_PIC_THRUST, SHIP_2_PIC_SHIELD, SHIP_2_KEYS, SHIP_2_JOY, SHIP_MAX_LIVES)

        self.ship_3 = Ship(self.game.screen_width, self.game.screen_height, 3, self.nb_player, SHIP3_X, SHIP3_Y, \
                            SHIP_3_PIC, SHIP_3_PIC_THRUST, SHIP_3_PIC_SHIELD, SHIP_3_KEYS, SHIP_3_JOY, SHIP_MAX_LIVES)

        self.ship_4 = Ship(self.game.screen_width, self.game.screen_height, 4, self.nb_player, SHIP4_X, SHIP4_Y, \
                            SHIP_4_PIC, SHIP_4_PIC_THRUST, SHIP_4_PIC_SHIELD, SHIP_4_KEYS, SHIP_4_JOY, SHIP_MAX_LIVES)

        self.ships.append(self.ship_1)
        
        if self.nb_player >= 2:
            self.ships.append(self.ship_2)
        if self.nb_player >= 3:
            self.ships.append(self.ship_3)
        if self.nb_player >= 4:
            self.ships.append(self.ship_4)

    def game_loop(self):

        while True:

            # events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.record_it()
                    sys.exit(0)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.record_it()
                        sys.exit(0)
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused

                    elif event.key == pygame.K_1:
                        self.set_level(1)
                    elif event.key == pygame.K_2:
                        self.set_level(2)
                    elif event.key == pygame.K_3:
                        self.set_level(3)
                    elif event.key == pygame.K_4:
                        self.set_level(4)
                    elif event.key == pygame.K_5:
                        self.set_level(5)
                    elif event.key == pygame.K_6:
                        self.set_level(6)
                    elif event.key == pygame.K_7:
                        self.set_level(7)

                    self.ship_key_down(event.key, self.ship_1, SHIP_1_KEYS)
                    self.ship_key_down(event.key, self.ship_2, SHIP_2_KEYS)
                    self.ship_key_down(event.key, self.ship_3, SHIP_3_KEYS)
                    self.ship_key_down(event.key, self.ship_4, SHIP_4_KEYS)

                elif event.type == pygame.KEYUP:
                    self.ship_key_up(event.key, self.ship_1, SHIP_1_KEYS)
                    self.ship_key_up(event.key, self.ship_2, SHIP_2_KEYS)
                    self.ship_key_up(event.key, self.ship_3, SHIP_3_KEYS)
                    self.ship_key_up(event.key, self.ship_4, SHIP_4_KEYS)

            # joystick
            for ship in self.ships:
                if ship.joystick_number:
                    try:
                        if pygame.joystick.Joystick(ship.joystick_number-1).get_button(0):
                            ship.thrust_pressed = True
                        else:
                            ship.thrust_pressed = False

                        if pygame.joystick.Joystick(ship.joystick_number-1).get_button(5):
                            ship.shoot_pressed = True
                        else:
                            ship.shoot_pressed = False

                        if pygame.joystick.Joystick(ship.joystick_number-1).get_button(1):
                            ship.shield_pressed = True
                        else:
                            ship.shield_pressed = False

                        horizontal_axis = pygame.joystick.Joystick(ship.joystick_number-1).get_axis(0)

                        if int(round(horizontal_axis)) == 1:
                            ship.right_pressed = True
                        else:
                            ship.right_pressed = False

                        if int(round(horizontal_axis)) == -1:
                            ship.left_pressed = True
                        else:
                            ship.left_pressed = False
                    except:
                        pass

            # core
            if not self.paused:
                # per level data
                self.map = self.game.getv("map", current_level=self.level)
                self.map_buffer = self.game.getv("map_buffer", current_level=self.level)
                self.map_buffer_mask = self.game.getv("map_buffer_mask", current_level=self.level)
                self.platforms = self.game.getv("platforms", current_level=self.level)

                # clear screen
                self.game.window.fill((0,0,0))

                self.map_buffer.blit(self.map, (0, 0))

                # update ship pos
                for ship in self.ships:
                    ship.update(self, ship.left_pressed, ship.right_pressed, ship.thrust_pressed, ship.shoot_pressed, ship.shield_pressed)

                # collide_map and ship tp ship
                for ship in self.ships:
                    ship.collide_map(self.map_buffer, self.map_buffer_mask, self.platforms)

                for ship in self.ships:
                    ship.collide_ship(self.ships)
                    
                for ship in self.ships:
                    ship.plot_shots(self.map_buffer)

                for ship in self.ships:
                    ship.explod_sequence(self)

                for ship in self.ships:
                    ship.collide_shots(self.ships)

                # blit ship in the map
                for ship in self.ships:
                    ship.draw(self.map_buffer)

                for ship in self.ships:

                    # clipping to avoid black when the ship is close to the edges
                    rx = ship.xpos - ship.view_width/2
                    ry = ship.ypos - ship.view_height/2
                    if rx < 0:
                        rx = 0
                    elif rx > (self.MAP_WIDTH - ship.view_width):
                        rx = (self.MAP_WIDTH - ship.view_width)
                    if ry < 0:
                        ry = 0
                    elif ry > (self.MAP_HEIGHT - ship.view_height):
                        ry = (self.MAP_HEIGHT - ship.view_height)

                    # blit the map area around the ship on the screen
                    sub_area1 = Rect(rx, ry, ship.view_width, ship.view_height)
                    self.game.window.blit(self.map_buffer, (ship.view_left, ship.view_top), sub_area1)

                # debug on screen
                self.screen_print_info()

                cv = (225, 225, 225)
                pygame.draw.line( self.game.window, cv, (0, int(self.game.screen_height/2)), (self.game.screen_width, int(self.game.screen_height/2)) )
                pygame.draw.line( self.game.window, cv, (int(self.game.screen_width/2), 0), (int(self.game.screen_width/2), (self.game.screen_height)) )

                # display
                pygame.display.flip()
                self.frames += 1


            self.clock.tick(self.max_fps)
            pygame.display.set_caption('Mayhem FPS=%.2f' % self.clock.get_fps())

            #print(self.clock.get_fps())

    def screen_print_info(self):
        # debug text
        if self.debug_print:
            ship_pos = self.myfont.render('Pos: %s %s' % (self.ship_1.xpos, self.ship_1.ypos), False, (255, 255, 255))
            self.game.window.blit(ship_pos, (DEBUG_TEXT_XPOS + 5, 30))

            ship_va = self.myfont.render('vx=%.2f, vy=%.2f, ax=%.2f, ay=%.2f' % (self.ship_1.vx,self.ship_1.vy, self.ship_1.ax, self.ship_1.ay), False, (255, 255, 255))
            self.game.window.blit(ship_va, (DEBUG_TEXT_XPOS + 5, 55))

            ship_angle = self.myfont.render('Angle: %s' % (self.ship_1.angle,), False, (255, 255, 255))
            self.game.window.blit(ship_angle, (DEBUG_TEXT_XPOS + 5, 80))

            dt = self.myfont.render('Frames: %s' % (self.frames,), False, (255, 255, 255))
            self.game.window.blit(dt, (DEBUG_TEXT_XPOS + 5, 105))

            fps = self.myfont.render('FPS: %.2f' % self.clock.get_fps(), False, (255, 255, 255))
            self.game.window.blit(fps, (DEBUG_TEXT_XPOS + 5, 130))

            #ship_lives = self.myfont.render('Lives: %s' % (self.ship_1.lives,), False, (255, 255, 255))
            #self.game.window.blit(ship_lives, (DEBUG_TEXT_XPOS + 5, 105))

# -------------------------------------------------------------------------------------------------

class GameWindow():

    def __init__(self, screen_width, screen_height):

        pygame.display.set_caption('Mayhem')

        self.screen_width = screen_width
        self.screen_height = screen_height

        self.window = pygame.display.set_mode((self.screen_width, self.screen_height), flags=pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE | pygame.SCALED)

        # Background
        self.map_1 = pygame.image.load(MAP_1).convert() # .convert_alpha()
        #self.map.set_colorkey( (0, 0, 0) ) # used for the mask, black = background
        #self.map_rect = self.map.get_rect()
        #self.map_mask = pygame.mask.from_surface(self.map)

        self.map_buffer_1 = self.map_1.copy() # pygame.Surface((self.map.get_width(), self.map.get_height()))

        self.map_buffer_1.set_colorkey( (0, 0, 0) )
        self.map_buffer_mask_1 = pygame.mask.from_surface(self.map_buffer_1)

        # map2
        self.map_2 = pygame.image.load(MAP_2).convert() # .convert_alpha()
        self.map_buffer_2 = self.map_2.copy() # pygame.Surface((self.map.get_width(), self.map.get_height()))

        self.map_buffer_2.set_colorkey( (0, 0, 0) )
        self.map_buffer_mask_2 = pygame.mask.from_surface(self.map_buffer_2)

        # map3
        self.map_3 = pygame.image.load(MAP_3).convert() # .convert_alpha()
        self.map_buffer_3 = self.map_3.copy() # pygame.Surface((self.map.get_width(), self.map.get_height()))

        self.map_buffer_3.set_colorkey( (0, 0, 0) )
        self.map_buffer_mask_3 = pygame.mask.from_surface(self.map_buffer_3)

        # map4
        self.map_4 = pygame.image.load(MAP_4).convert() # .convert_alpha()
        self.map_buffer_4 = self.map_4.copy() # pygame.Surface((self.map.get_width(), self.map.get_height()))

        self.map_buffer_4.set_colorkey( (0, 0, 0) )
        self.map_buffer_mask_4 = pygame.mask.from_surface(self.map_buffer_4)

        # map5
        self.map_5 = pygame.image.load(MAP_5).convert() # .convert_alpha()
        self.map_buffer_5 = self.map_5.copy() # pygame.Surface((self.map.get_width(), self.map.get_height()))

        self.map_buffer_5.set_colorkey( (0, 0, 0) )
        self.map_buffer_mask_5 = pygame.mask.from_surface(self.map_buffer_5)

        # map6
        self.map_6 = pygame.image.load(MAP_6).convert() # .convert_alpha()
        self.map_buffer_6 = self.map_6.copy() # pygame.Surface((self.map.get_width(), self.map.get_height()))

        self.map_buffer_6.set_colorkey( (0, 0, 0) )
        self.map_buffer_mask_6 = pygame.mask.from_surface(self.map_buffer_6)

        # map7
        self.map_7 = pygame.image.load(MAP_7).convert() # .convert_alpha()
        self.map_buffer_7 = self.map_7.copy() # pygame.Surface((self.map.get_width(), self.map.get_height()))

        self.map_buffer_7.set_colorkey( (0, 0, 0) )
        self.map_buffer_mask_7 = pygame.mask.from_surface(self.map_buffer_7)

        # platforms
        self.platforms_1 = [ ( 464, 513, 333 ),
                            ( 60, 127, 1045 ),
                            ( 428, 497, 531 ),
                            ( 504, 568, 985 ),
                            ( 178, 241, 875 ),
                            ( 8, 37, 187 ),
                            ( 302, 351, 271 ),
                            ( 434, 521, 835 ),
                            ( 499, 586, 1165 ),
                            ( 68, 145, 1181 ) ]

        self.platforms_2 = [ [ 201, 259, 175 ],
                            [ 21, 92, 1087 ],
                            [ 552, 615, 513 ],
                            [ 468, 525, 915 ],
                            [ 546, 599, 327 ],
                            [ 8, 37, 187 ],
                            [ 660, 697, 447 ],
                            [ 350, 435, 621 ],
                            [ 596, 697, 1141 ] ]

        self.platforms_3 = [ [ 14, 65, 111 ],
                            [ 38, 93, 1121 ],
                            [ 713, 760, 231 ],
                            [ 473, 540, 617 ],
                            [ 565, 616, 459 ],
                            [ 343, 398, 207 ],
                            [ 316, 385, 805 ],
                            [ 492, 548, 987 ],
                            [ 66, 145, 1180 ] ]

        self.platforms_4 = [ [ 19, 69, 111 ],
                            [ 32, 84, 1121 ],
                            [ 705, 755, 231],
                            [ 487, 547, 617 ],
                            [ 556, 607, 459 ],
                            [ 344, 393, 207 ],
                            [ 326, 377, 805 ],
                            [ 502, 554, 987 ],
                            [ 66, 145, 1180 ] ]

        self.platforms_5 = [ [ 504, 568, 985 ],
                            [ 464, 513, 333 ],
                            [ 428, 497, 531],
                            [ 178, 241, 875 ],
                            [ 8, 37, 187 ],
                            [ 302, 351, 271 ],
                            [ 434, 521, 835 ],
                            [ 434, 521, 835 ],
                            [ 60, 127, 1045 ],
                            [ 348, 377, 1089 ],
                            [ 499, 586, 1165 ],
                            [ 68, 145, 1181 ] ]

        self.platforms_6 = [ 
                            [464, 513, 333],  [60, 127, 1045], [428, 497, 531], [504, 568, 985],
                            [178, 241, 875],  [8, 37, 187],    [302, 351, 271], [434, 521, 835],
                            [499, 586, 1165], [68, 145, 1181],

                            [993, 1051, 175], [813, 884, 1087], [1344, 1407, 513], [1260, 1317, 915], [1338, 1391, 327], [1452, 1489, 447], [1142, 1227, 621], [1388, 1489, 1141],
                            [806, 857, 1311], [830, 885, 2321], [1505, 1552, 1431], [1265, 1332, 1817], [1357, 1408, 1659], [1135, 1190, 1407], [1108, 1177, 2005], [1284, 1340, 2187], [858, 937, 2380],
                            [19, 69, 1311], [32, 84, 2321], [705, 755, 1431], [487, 547, 1817], [556, 607, 1659], [344, 393, 1407], [326, 377, 2005], [502, 554, 2187], [66, 145, 2380]]

        self.platforms_7 = [ 
                            [464, 513, 333],  [60, 127, 1045], [428, 497, 531], [504, 568, 985],
                            [178, 241, 875],  [8, 37, 187],    [302, 351, 271], [434, 521, 835],
                            [499, 586, 1165], [68, 145, 1181],

                            [993, 1051, 175], [813, 884, 1087], [1344, 1407, 513], [1260, 1317, 915], [1338, 1391, 327], [1452, 1489, 447], [1142, 1227, 621], [1388, 1489, 1141],
                            [806, 857, 1311], [830, 885, 2321], [1505, 1552, 1431], [1265, 1332, 1817], [1357, 1408, 1659], [1135, 1190, 1407], [1108, 1177, 2005], [1284, 1340, 2187], [858, 937, 2380],
                            [19, 69, 1311], [32, 84, 2321], [705, 755, 1431], [487, 547, 1817], [556, 607, 1659], [344, 393, 1407], [326, 377, 2005], [502, 554, 2187], [66, 145, 2380],

                            [504, 568, 3385], [464, 513, 2733], [428, 497, 2931], [178, 241, 3275], [8, 37, 2587], [302, 351, 2671], [434, 521, 3235], [434, 521, 3235], [60, 127, 3445], [348, 377, 3489], [499, 586, 3565], [68, 145, 3581],
                            [1296, 1360, 3385], [1256, 1305, 2733], [1220, 1289, 2931], [970, 1033, 3275], [800, 829, 2587], [1094, 1143, 2671], [1226, 1313, 3235], [1226, 1313, 3235], [852, 919, 3445], [1140, 1169, 3489], [1291, 1378, 3565], [860, 937, 3581]]

    def getv(self, name, current_level=1):
        return getattr(self, "%s_%s" % (name, str(current_level)))

# -------------------------------------------------------------------------------------------------

def run():
    #pygame.mixer.pre_init(frequency=22050)
    pygame.init()
    #pygame.display.init()

    pygame.mouse.set_visible(False)
    pygame.font.init()
    pygame.mixer.init() # frequency=22050

    #pygame.event.set_blocked((MOUSEMOTION, MOUSEBUTTONUP, MOUSEBUTTONDOWN))

    # joystick
    pygame.joystick.init()
    joystick_count = pygame.joystick.get_count()
    print("joystick_count", joystick_count)

    for i in range(joystick_count):
        j = pygame.joystick.Joystick(i)
        j.init()

    # options
    parser = argparse.ArgumentParser()

    parser.add_argument('-width', '--width', help='', type=int, action="store", default=1200)
    parser.add_argument('-height', '--height', help='', type=int, action="store", default=800)
    parser.add_argument('-np', '--nb_player', help='', type=int, action="store", default=4)
    parser.add_argument('-fps', '--fps', help='', type=int, action="store", default=60)
    parser.add_argument('-dp', '--debug_print', help='', action="store", default=False)

    parser.add_argument('-m', '--motion', help='How the ship moves', action="store", default='gravity', choices=("basic", "thrust", "gravity"))
    parser.add_argument('-r', '--record_play', help='', action="store", default="")
    parser.add_argument('-pr', '--play_recorded', help='', action="store", default="")

    result = parser.parse_args()
    args = dict(result._get_kwargs())

    print("Args=", args)

    # window
    game_window = GameWindow(args["width"], args["height"])

    env = MayhemEnv(game_window, level=1, max_fps=args["fps"], debug_print=args["debug_print"], nb_player=args["nb_player"], motion=args["motion"], \
                    record_play=args["record_play"], play_recorded=args["play_recorded"])

    env.main_loop()

# -------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    run()
