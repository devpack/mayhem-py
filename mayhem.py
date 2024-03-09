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

python3 mayhem.py

python3 mayhem.py --server=ws://127.0.0.1:9000 --player_name=tony --ship_control=k1 -sap

python3 mayhem.py --server=ws://127.0.0.1:9000 --player_name=tony --ship_control=k1 -zoom
python3 mayhem.py --server=ws://192.168.1.75:9000 --player_name=alex --ship_control=j1 -sap

"""

import os, sys, argparse, random, math, time, pickle, json, enum
from random import randint
import collections

from twisted.internet import reactor
from twisted.internet import task
from twisted.internet.protocol import ReconnectingClientFactory
from autobahn.twisted.websocket import WebSocketClientFactory, WebSocketClientProtocol, connectWS

import pygame
from pygame import gfxdraw
from pygame.locals import *

import pygame_menu

import numpy as np
import moderngl as mgl
from shader_program import ShaderProgram

import imgui
import my_imgui.pygame_imgui as pygame_imgui

try:
    import msgpack
    USE_JSON = False
except:
    USE_JSON = True

# -------------------------------------------------------------------------------------------------
# General

DEBUG_TEXT_XPOS = 0

WHITE    = (255, 255, 255)
RED      = (255, 0, 0)
LVIOLET  = (128, 0, 128)

USE_MINI_MASK = True # mask the size of the ship (instead of the player view size)

# -------------------------------------------------------------------------------------------------
# SHIP dynamics

SHIP_ANGLE_LAND = 30
SHIP_MAX_LIVES = 10
SHIP_SPRITE_SIZE = 32

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

MARGIN_SIZE = 0
W_PERCENT   = 1.0
H_PERCENT   = 1.0

# -------------------------------------------------------------------------------------------------

class FPSCounter:
    def __init__(self):
        self.time = time.perf_counter()
        self.frame_times = collections.deque(maxlen=60)

    def tick(self):
        t1 = time.perf_counter()
        dt = t1 - self.time
        self.time = t1
        self.frame_times.append(dt)

    def get_fps(self):
        total_time = sum(self.frame_times)
        if total_time == 0:
            return 0
        else:
            return len(self.frame_times) / sum(self.frame_times)
        
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

    def __init__(self, screen_width, screen_height, show_all_players, ship_number, xpos, ypos, ship_pic, ship_pic_thrust, ship_pic_shield, joystick_number, lives):

        # renders only one player, in big
        if not show_all_players:
            self.view_width  = screen_width
            self.view_height = screen_height
            self.view_left = MARGIN_SIZE
            self.view_top = MARGIN_SIZE
        # renders all the players, split the screen in 4
        else:
            self.view_width  = int((screen_width * W_PERCENT) / 2)
            self.view_height = int((screen_height * H_PERCENT) / 2)

            if ship_number == "1":
                self.view_left = MARGIN_SIZE
                self.view_top = MARGIN_SIZE

            elif ship_number == "2":
                self.view_left = MARGIN_SIZE + self.view_width + MARGIN_SIZE
                self.view_top = MARGIN_SIZE

            elif ship_number == "3":
                self.view_left = MARGIN_SIZE
                self.view_top = MARGIN_SIZE + self.view_height + MARGIN_SIZE

            elif ship_number == "4":
                self.view_left = MARGIN_SIZE + self.view_width + MARGIN_SIZE
                self.view_top = MARGIN_SIZE + self.view_height + MARGIN_SIZE

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
        self.game_over = False
        self.last_landed_pos = (self.init_xpos, self.init_ypos)

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

        self.joystick_number = joystick_number

    def reset(self):

        if 0:
            self.xpos = self.init_xpos
            self.ypos = self.init_ypos
        else:
            self.xpos, self.ypos = self.last_landed_pos

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
        if self.lives == 0:
            self.game_over = True

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
                # draw explosion
                ship_cx = self.xpos + SHIP_SPRITE_SIZE/2;
                ship_cy = self.ypos + SHIP_SPRITE_SIZE/2;

                c = max(0, 200 - self.explod_tick)

                for p in range(0, int((240 - self.explod_tick)/4)):           
                    r = (32-(self.explod_tick*2)) * math.sqrt(random.uniform(0, 1))
                    theta = random.uniform(0, 1) * 2 * math.pi;
                    x = r * math.cos(theta);
                    y = r * math.sin(theta);

                    gfxdraw.pixel(env.map_buffer, int(ship_cx + x) , int(ship_cy + y), (c, c, c))

                # debris
                for deb in self.debris:

                    # move debris
                    deb.ax = deb.impultion * -math.cos(math.radians(90 - deb.angle))
                    deb.ay = env.iG*5 + (deb.impultion * -math.sin(math.radians(90 - deb.angle)))

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

        if self.explod or self.game_over:
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
                self.angle += env.SHIP_ANGLESTEP
            if right_pressed:
                self.angle -= env.SHIP_ANGLESTEP

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
                    self.thrust = env.SHIP_THRUST_MAX

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
                    self.angle += env.SHIP_ANGLESTEP
                if right_pressed:
                    self.angle -= env.SHIP_ANGLESTEP

                # 
                self.angle = self.angle % 360

                # https://gafferongames.com/post/integration_basics/
                self.ax = self.thrust * -math.cos( math.radians(90 - self.angle) ) # ax = thrust * sin1
                self.ay = env.iG + (self.thrust * -math.sin( math.radians(90 - self.angle))) # ay = g + thrust * (-cos1)

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

    def plot_shots(self, map_buffer, shots):
        for shot in list(shots): # copy of self.shots
            shot.xposprecise += shot.dx
            shot.yposprecise += shot.dy
            shot.x = int(shot.xposprecise)
            shot.y = int(shot.yposprecise)

            try:
                c = map_buffer.get_at((int(shot.x), int(shot.y)))
                if (c.r != 0) or (c.g != 0) or (c.b != 0):
                    shots.remove(shot)

                gfxdraw.pixel(map_buffer, int(shot.x) , int(shot.y), WHITE)
                #pygame.draw.circle(map_buffer, WHITE, (int(shot.x) , int(shot.y)), 1)
                #pygame.draw.line(map_buffer, WHITE, (int(self.xpos + SHIP_SPRITE_SIZE/2), int(self.ypos + SHIP_SPRITE_SIZE/2)), (int(shot.x), int(shot.y)))

            # out of surface
            except IndexError:
                shots.remove(shot)

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

                #if ( (-1.0/env.SLOW_DOWN_COEF <= self.vx) and (self.vx < 1.0/env.SLOW_DOWN_COEF) and (-1.0/env.SLOW_DOWN_COEF < self.vy) and (self.vy < 1.0/env.SLOW_DOWN_COEF) ):
                if ( (-1.0 <= self.vx) and (self.vx < 1.0) and (-1.0 < self.vy) and (self.vy < 1.0) ):
                    self.landed = True
                    self.last_landed_pos = (self.xpos, self.ypos)
                    self.bounce = False
                else:
                    self.bounce = True
                    self.last_landed_pos = (self.xpos, self.ypos)
                    self.sound_bounce.play()

                # no need to check other platforms
                break

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

        if self.explod or self.game_over:
            return
        
        map_buffer.blit(self.image_rotated, (self.xpos + self.rot_xoffset, self.ypos + self.rot_yoffset))

    def collide_map(self, map_buffer, map_buffer_mask, platforms):

        if self.explod or self.game_over:
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
        
        if self.explod or self.game_over:
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
                                ship.impactx = deb.vx
                                ship.impacty = deb.vy
                    # out of ship mask => no collision
                    except IndexError:
                        pass

# -------------------------------------------------------------------------------------------------

class MayhemEnv():
    
    def __init__(self, game, level=6, max_fps=60, debug_print=1, motion="gravity", record_play="", 
                 play_recorded="", player_name="tony", show_all_players=False, ship_control="k1", 
                 game_client_factory=None):

        self.myfont = pygame.font.SysFont('Arial', 20)
        self.myfont_big = pygame.font.SysFont('Arial', 48, bold=True)

        self.player_name = player_name
        self.ship_control = ship_control
        self.show_all_players = show_all_players

        # Websoket game client
        self.game_client_factory = game_client_factory
        if self.game_client_factory:
            self.game_client_factory.player_name = player_name

        # screen
        self.game = game

        self.game.screen.fill((0, 0, 0))

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

        self.lastTime = time.time()
        self.currentTime = time.time()
        self.fps = FPSCounter()

        # per level data
        self.map = self.game.getv("map", current_level=self.level)
        self.map_buffer = self.game.getv("map_buffer", current_level=self.level)
        self.map_buffer_mask = self.game.getv("map_buffer_mask", current_level=self.level)
        self.platforms = self.game.getv("platforms", current_level=self.level)

        # game physics
        self.SHIP_THRUST_MAX    = 0.18
        self.iG                 = 0.05
        self.SHIP_ANGLESTEP     = 5

        # joystick if any
        if self.game_client_factory:
            joystick_number = 0
            if self.ship_control == "j1":
                joystick_number = 1
            elif self.ship_control == "j2":
                joystick_number = 2

            self.joystick = None
            if joystick_number:
                try:
                    self.joystick = pygame.joystick.Joystick(joystick_number-1)
                except Exception as e:
                    print("Failed to create joystick %s : %s" % (str(joystick_number-1), repr(e)))
        else:
            try:
                self.joy1 = pygame.joystick.Joystick(0)
            except Exception as e:
                self.joy1 = None
                print("Failed to create joystick 0 : %s" % repr(e))
            try:
                self.joy2 = pygame.joystick.Joystick(1)
            except Exception as e:
                self.joy2 = None
                print("Failed to create joystick 1 : %s" % repr(e))

        self.set_level_and_ships(self.level)

    def get_fps(self):
        self.currentTime = time.time()
        delta = self.currentTime - self.lastTime

        if delta >= 1:
            #fps = f"PyGame FPS: {self.fps.get_fps():3.0f}"
            gl_mode = "Non OpenGL"
            if self.game.use_opengl:
                gl_mode = "OpenGL"
            fps = 'Mayhem FPS (%s)=%.2f' % (gl_mode, self.fps.get_fps())
            pygame.display.set_caption(fps)

            self.lastTime = self.currentTime

        self.fps.tick()

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
            
    def set_level_and_ships(self, level_nb, force=False):

        change_level_allowed = True

        if self.game_client_factory:
            if self.game_client_factory.ship_number != "1":
                change_level_allowed = False

        if change_level_allowed or force:
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

            # lives
            lives = SHIP_MAX_LIVES
            try:
                if self.ship_1:
                    lives = self.ship_1.lives
            except:
                pass  
            self.ship_1 = Ship(self.game.screen_width, self.game.screen_height, self.show_all_players, "1", SHIP1_X, SHIP1_Y,
                                    SHIP_1_PIC, SHIP_1_PIC_THRUST, SHIP_1_PIC_SHIELD, SHIP_1_JOY, lives)

            lives = SHIP_MAX_LIVES
            try:
                if self.ship_2:
                    lives = self.ship_2.lives
            except:
                pass
            self.ship_2 = Ship(self.game.screen_width, self.game.screen_height, self.show_all_players, "2", SHIP2_X, SHIP2_Y,
                                SHIP_2_PIC, SHIP_2_PIC_THRUST, SHIP_2_PIC_SHIELD, SHIP_2_JOY, lives)

            lives = SHIP_MAX_LIVES
            try:
                if self.ship_3:
                    lives = self.ship_3.lives
            except:
                pass
            self.ship_3 = Ship(self.game.screen_width, self.game.screen_height, self.show_all_players, "3", SHIP3_X, SHIP3_Y,
                                SHIP_3_PIC, SHIP_3_PIC_THRUST, SHIP_3_PIC_SHIELD, SHIP_3_JOY, lives)
            
            lives = SHIP_MAX_LIVES
            try:
                if self.ship_4:
                    lives = self.ship_4.lives
            except:
                pass
            self.ship_4 = Ship(self.game.screen_width, self.game.screen_height, self.show_all_players, "4", SHIP4_X, SHIP4_Y,
                                SHIP_4_PIC, SHIP_4_PIC_THRUST, SHIP_4_PIC_SHIELD, SHIP_4_JOY, lives)

            self.ships = [self.ship_1, self.ship_2, self.ship_3, self.ship_4]

    def show_options_ui(self):
        imgui.new_frame()
        imgui.begin("Options", True)

        _, self.SHIP_THRUST_MAX = imgui.slider_float("thrust", self.SHIP_THRUST_MAX, 0.05, 0.5)
        _, self.iG              = imgui.slider_float("G", self.iG, 0.01, 0.1)
        _, self.SHIP_ANGLESTEP  = imgui.slider_float("rot", self.SHIP_ANGLESTEP, 1, 10)

        imgui.end()

    def game_loop(self):

        # we are using twisted loop so no while 1 + self.clock.tick(self.max_fps)
        #while True:

        # online play ?
        if self.game_client_factory:
            if self.game_client_factory._state == Action.PLAY:
                play_now = True
            elif self.game_client_factory._state == Action.EXITED:
                for ship in self.ships:
                    ship.reset()
                play_now = False
                if self.game.use_opengl:
                    self.game.frame_tex.release()
                reactor.stop()
            else:
                play_now = False

        # local play
        else:
            play_now = True

        # play loop
        if play_now:

            if self.game_client_factory:

                # 1. -------
                # Set our player status in self.game_client_factory: will be send each time we received a message action = Action.PLAYER_UPDATE_REQUEST

                # self.game_client_factory.ship_number is set by the server when we logged
                self.ship_x = getattr(self, "ship_%s" % self.game_client_factory.ship_number)
                self.ship_x.player_name = self.player_name

                # player_name set in init()
                # { "ship_number":"3", "player_name":"tony, "level":"6", "xpos":"412", "ypos":"517", "angle":"250", "tp":"True", "sp":"False", "shots":[(x,y), (x2, y2), ...] }
                self.game_client_factory.level     = self.level # only ship_1 can set the level number
                self.game_client_factory.xpos      = self.ship_x.xposprecise
                self.game_client_factory.ypos      = self.ship_x.yposprecise
                self.game_client_factory.angle     = self.ship_x.angle
                self.game_client_factory.tp        = self.ship_x.thrust_pressed
                self.game_client_factory.sp        = self.ship_x.shield_pressed
                self.game_client_factory.landed    = self.ship_x.landed
                self.game_client_factory.game_over = self.ship_x.game_over

                particles = []
                for s in self.ship_x.shots:
                    particles.append((s.x, s.y))
                #for d in self.ship_x.debris:
                #    particles.append((d.x, d.y))

                self.game_client_factory.shots  = particles

                # 2. -------
                # Get other players status if any

                self.other_ships = []

                others = ["1", "2", "3", "4"]
                others.remove(self.game_client_factory.ship_number) # remove ourself from the list

                for ship_number in others:
                    try:
                        ship_update = getattr(self.game_client_factory, "other_player_%s" % ship_number)
                    except:
                        ship_update = None

                    if ship_update:
                        self.other_ships.append(ship_update)

                #print("other_ships=", self.other_ships)

                # 1. self.ship_x is the ship we play with, this will update its posx etc. and we change the states of self.game_client_factory based on that
                #    then our player xpos etc. will be transmitted throught self.game_client_factory each time we receive a message Action.PLAYER_UPDATE_REQUEST
                #
                # 2. self.other_ships contains the other ships last updates we got from the server (message Action.OTHER_PLAYER_UPDATE)
                #    then we need to render those ships and process collision etc accordingly

                ship_keys = SHIP_2_KEYS
                if self.ship_control == "k2":
                    ship_keys = SHIP_1_KEYS

                # events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.record_it()
                        if self.game.use_opengl:
                            self.game.frame_tex.release()
                        reactor.stop()
                        #sys.exit(0)

                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.record_it()
                            if self.game.use_opengl:
                                self.game.frame_tex.release()
                            reactor.stop()
                            #sys.exit(0)
                        elif event.key == pygame.K_p:
                            self.paused = not self.paused

                        elif event.key == pygame.K_1:
                            self.set_level_and_ships(1)
                        elif event.key == pygame.K_2:
                            self.set_level_and_ships(2)
                        elif event.key == pygame.K_3:
                            self.set_level_and_ships(3)
                        elif event.key == pygame.K_4:
                            self.set_level_and_ships(4)
                        elif event.key == pygame.K_5:
                            self.set_level_and_ships(5)
                        elif event.key == pygame.K_6:
                            self.set_level_and_ships(6)
                        elif event.key == pygame.K_7:
                            self.set_level_and_ships(7)

                        self.ship_key_down(event.key, self.ship_x, ship_keys)

                    elif event.type == pygame.KEYUP:
                        self.ship_key_up(event.key, self.ship_x, ship_keys)

                    # imgui event
                    if self.game.use_opengl and self.game.show_options:
                        self.game.imgui_renderer.process_event(event)

                # joystick
                if self.joystick:
                    try:
                        if self.joystick.get_button(0):
                            self.ship_x.thrust_pressed = True
                        else:
                            self.ship_x.thrust_pressed = False

                        if self.joystick.get_button(5):
                            self.ship_x.shoot_pressed = True
                        else:
                            self.ship_x.shoot_pressed = False

                        if self.joystick.get_button(1):
                            self.ship_x.shield_pressed = True
                        else:
                            self.ship_x.shield_pressed = False

                        horizontal_axis = self.joystick.get_axis(0)

                        if int(round(horizontal_axis)) == 1:
                            self.ship_x.right_pressed = True
                        else:
                            self.ship_x.right_pressed = False

                        if int(round(horizontal_axis)) == -1:
                            self.ship_x.left_pressed = True
                        else:
                            self.ship_x.left_pressed = False
                    except:
                        pass

                # per level data
                self.map = self.game.getv("map", current_level=self.level)
                self.map_buffer = self.game.getv("map_buffer", current_level=self.level)
                self.map_buffer_mask = self.game.getv("map_buffer_mask", current_level=self.level)
                self.platforms = self.game.getv("platforms", current_level=self.level)

                # clear screen
                self.game.screen.fill((0,0,0))

                self.map_buffer.blit(self.map, (0, 0))

                # update ship pos
                self.ship_x.update(self, self.ship_x.left_pressed, self.ship_x.right_pressed, self.ship_x.thrust_pressed, 
                                   self.ship_x.shoot_pressed, self.ship_x.shield_pressed)

                self.active_ships = []
                self.active_ships.append(self.ship_x)

                # { "ship_number":"3", "player_name":"tony, "level":"6", "xpos":"412", "ypos":"517", "angle":"250", "tp":"True", "sp":"False", "shots":[(x,y), (x2, y2), ...] }
                for other_ship in self.other_ships:
                    o_ship = getattr(self, "ship_%s" % other_ship["ship_number"])
                    
                    # only ship 1 can change the level, so for this case we are not ship 1
                    # but ship 1 changed the level, so we follow and change the level (possible only with force=1)
                    if (other_ship["ship_number"] == "1") and (other_ship["level"] != self.level):
                        self.set_level_and_ships(other_ship["level"], force=True)

                    o_ship.player_name = other_ship["player_name"]

                    o_ship.xpos   = other_ship["xpos"]
                    o_ship.ypos   = other_ship["ypos"]
                    o_ship.angle  = other_ship["angle"]
                    o_ship.landed = other_ship["landed"]
                    o_ship.thrust_pressed = other_ship["tp"]
                    o_ship.shield_pressed = other_ship["sp"]
                    o_ship.game_over = other_ship["game_over"]

                    if other_ship["tp"]:
                        o_ship.thrust = True
                    else:
                        o_ship.thrust = False

                    if other_ship["sp"]:
                        o_ship.shield = True
                    else:
                        o_ship.shield = False

                    o_ship.image = o_ship.ship_pic
                    if o_ship.shield_pressed:
                        o_ship.image = o_ship.ship_pic_shield
                    if o_ship.thrust_pressed:
                        o_ship.image = o_ship.ship_pic_thrust

                    o_ship.image_rotated = pygame.transform.rotate(o_ship.image, o_ship.angle)
                    o_ship.mask = pygame.mask.from_surface(o_ship.image_rotated)

                    rect = o_ship.image_rotated.get_rect()
                    o_ship.rot_xoffset = int( ((SHIP_SPRITE_SIZE - rect.width)/2) )  # used in draw() and collide_map()
                    o_ship.rot_yoffset = int( ((SHIP_SPRITE_SIZE - rect.height)/2) ) # used in draw() and collide_map()

                    o_shots = []
                    for o_shot in other_ship["shots"]:
                        shot = Shot()
                        shot.x = o_shot[0]
                        shot.xposprecise = o_shot[0]
                        shot.y = o_shot[1]
                        shot.yposprecise = o_shot[1]

                        o_shots.append(shot)

                    o_ship.shots = o_shots

                    self.active_ships.append(o_ship)

                # collide_map
                for ship in self.active_ships:
                    ship.collide_map(self.map_buffer, self.map_buffer_mask, self.platforms)

                for ship in self.active_ships:
                    ship.collide_ship(self.active_ships)
                    
                for ship in self.active_ships:
                    ship.plot_shots(self.map_buffer, ship.shots)

                for ship in self.active_ships:
                    ship.explod_sequence(self)

                for ship in self.active_ships:
                    ship.collide_shots(self.active_ships)

                # blit ship in the map
                for ship in self.active_ships:
                    ship.draw(self.map_buffer)

                # blit the map area around the ship on the screen
                for ship in self.active_ships:

                    if not self.show_all_players:
                        if ship != self.ship_x:
                            continue

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

                    sub_area1 = Rect(rx, ry, ship.view_width, ship.view_height)

                    self.game.screen.blit(self.map_buffer, (ship.view_left, ship.view_top), sub_area1)
                        
                # debug on screen
                self.screen_print_info()

                # split lines
                if self.show_all_players:
                    cv = (225, 225, 225)
                    pygame.draw.line( self.game.screen, cv, (0, int(self.game.screen_height/2)), (self.game.screen_width, int(self.game.screen_height/2)) )
                    pygame.draw.line( self.game.screen, cv, (int(self.game.screen_width/2), 0), (int(self.game.screen_width/2), (self.game.screen_height)) )

                if self.game.use_opengl:
                    self.game.set_uniform(self.game.screen_program, "time", self.frames)

                    try:
                        self.game.frame_tex.write(self.game.display.get_view('1'))
                        #self.frame_tex.write(self.display.get_buffer())
                    except:
                        pass

                    self.game.vao.render(mode=mgl.TRIANGLE_STRIP)

                    if self.game.show_options:
                        self.show_options_ui()
                        imgui.render()
                        self.game.imgui_renderer.render(imgui.get_draw_data())

                # display
                pygame.display.flip()
                self.frames += 1

            # local play
            else:

                # events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.record_it()
                        if self.game.use_opengl:
                            self.game.frame_tex.release()
                        reactor.stop()
                        #sys.exit(0)

                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.record_it()
                            if self.game.use_opengl:
                                self.game.frame_tex.release()
                            reactor.stop()
                            #sys.exit(0)
                        elif event.key == pygame.K_p:
                            self.paused = not self.paused

                        elif event.key == pygame.K_1:
                            self.set_level_and_ships(1)
                        elif event.key == pygame.K_2:
                            self.set_level_and_ships(2)
                        elif event.key == pygame.K_3:
                            self.set_level_and_ships(3)
                        elif event.key == pygame.K_4:
                            self.set_level_and_ships(4)
                        elif event.key == pygame.K_5:
                            self.set_level_and_ships(5)
                        elif event.key == pygame.K_6:
                            self.set_level_and_ships(6)
                        elif event.key == pygame.K_7:
                            self.set_level_and_ships(7)

                        self.ship_key_down(event.key, self.ship_1, SHIP_1_KEYS)
                        self.ship_key_down(event.key, self.ship_2, SHIP_2_KEYS)
                        self.ship_key_down(event.key, self.ship_3, SHIP_3_KEYS)
                        self.ship_key_down(event.key, self.ship_4, SHIP_4_KEYS)

                    elif event.type == pygame.KEYUP:
                        self.ship_key_up(event.key, self.ship_1, SHIP_1_KEYS)
                        self.ship_key_up(event.key, self.ship_2, SHIP_2_KEYS)
                        self.ship_key_up(event.key, self.ship_3, SHIP_3_KEYS)
                        self.ship_key_up(event.key, self.ship_4, SHIP_4_KEYS)

                    # imgui event
                    if self.game.use_opengl and self.game.show_options:
                        self.game.imgui_renderer.process_event(event)

                # joystick
                for ship in self.ships:
                    if ship.joystick_number:

                        if ship.joystick_number == 1:
                            joy = self.joy1
                        elif ship.joystick_number == 2:
                            joy = self.joy2

                        try:
                            if joy.get_button(0):
                                ship.thrust_pressed = True
                            else:
                                ship.thrust_pressed = False

                            if joy.get_button(5):
                                ship.shoot_pressed = True
                            else:
                                ship.shoot_pressed = False

                            if joy.get_button(1):
                                ship.shield_pressed = True
                            else:
                                ship.shield_pressed = False

                            horizontal_axis = joy.get_axis(0)

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
                    self.game.screen.fill((0,0,0))

                    self.map_buffer.blit(self.map, (0, 0))

                    # update ship pos
                    for ship in self.ships:
                        ship.update(self, ship.left_pressed, ship.right_pressed, ship.thrust_pressed, ship.shoot_pressed, ship.shield_pressed)

                    # collide_map
                    for ship in self.ships:
                        ship.collide_map(self.map_buffer, self.map_buffer_mask, self.platforms)

                    for ship in self.ships:
                        ship.collide_ship(self.ships)
                        
                    for ship in self.ships:
                        ship.plot_shots(self.map_buffer, ship.shots)

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
                        self.game.screen.blit(self.map_buffer, (ship.view_left, ship.view_top), sub_area1)

                    # debug on screen
                    self.screen_print_info()

                    cv = (225, 225, 225)
                    pygame.draw.line( self.game.screen, cv, (0, int(self.game.screen_height/2)), (self.game.screen_width, int(self.game.screen_height/2)) )
                    pygame.draw.line( self.game.screen, cv, (int(self.game.screen_width/2), 0), (int(self.game.screen_width/2), (self.game.screen_height)) )

                    if self.game.use_opengl:
                        self.game.set_uniform(self.game.screen_program, "time", self.frames)

                        try:
                            self.game.frame_tex.write(self.game.display.get_view('1'))
                            #self.frame_tex.write(self.display.get_buffer())
                        except:
                            pass

                        self.game.vao.render(mode=mgl.TRIANGLE_STRIP)

                        if self.game.show_options:
                            self.show_options_ui()
                            imgui.render()
                            self.game.imgui_renderer.render(imgui.get_draw_data())

                    # display
                    pygame.display.flip()
                    self.frames += 1


            # we are using twisted loop so remove next line
            #self.clock.tick(self.max_fps)
                
            self.get_fps()
            #print(self.clock.get_fps())

    def screen_print_info(self):

        # player names
        if self.game_client_factory:
            if self.show_all_players:
                for ship in self.active_ships:
                    pn = self.myfont.render('%s' % (ship.player_name, ), False, (255, 255, 0))
                    self.game.screen.blit(pn, (ship.view_left, ship.view_top))

            # lives
            for ship in self.active_ships:
                offset = 0
                if self.show_all_players:
                    offset = 20
                lives = self.myfont.render('%s' % (ship.lives, ), False, (255, 255, 0))
                self.game.screen.blit(lives, (ship.view_left, ship.view_top + offset))

            # game over
            for ship in self.active_ships:
                if ship.game_over:
                    go = self.myfont_big.render('GAME OVER', False, (255, 0, 0))
                    self.game.screen.blit(go, (ship.view_left, ship.view_top + offset + 20))

        # debug text
        if self.debug_print:
            ship_pos = self.myfont.render('Pos: %s %s' % (self.ship_1.xpos, self.ship_1.ypos), False, (255, 255, 255))
            self.game.screen.blit(ship_pos, (DEBUG_TEXT_XPOS + 5, 30))

            ship_va = self.myfont.render('vx=%.2f, vy=%.2f, ax=%.2f, ay=%.2f' % (self.ship_1.vx,self.ship_1.vy, self.ship_1.ax, self.ship_1.ay), False, (255, 255, 255))
            self.game.screen.blit(ship_va, (DEBUG_TEXT_XPOS + 5, 55))

            ship_angle = self.myfont.render('Angle: %s' % (self.ship_1.angle,), False, (255, 255, 255))
            self.game.screen.blit(ship_angle, (DEBUG_TEXT_XPOS + 5, 80))

            dt = self.myfont.render('Frames: %s' % (self.frames,), False, (255, 255, 255))
            self.game.screen.blit(dt, (DEBUG_TEXT_XPOS + 5, 105))

            fps = self.myfont.render('FPS: %.2f' % self.clock.get_fps(), False, (255, 255, 255))
            self.game.screen.blit(fps, (DEBUG_TEXT_XPOS + 5, 130))

            #ship_lives = self.myfont.render('Lives: %s' % (self.ship_1.lives,), False, (255, 255, 255))
            #self.game.screen.blit(ship_lives, (DEBUG_TEXT_XPOS + 5, 105))


# -------------------------------------------------------------------------------------------------

class GameWindow():

    def __init__(self, screen_width, screen_height, zoom=False, use_opengl=False, show_options=False):

        pygame.display.set_caption('Mayhem')

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.use_opengl = use_opengl
        self.show_options = show_options

        f = pygame.RESIZABLE
        
        if use_opengl:
            f |= pygame.DOUBLEBUF | pygame.OPENGL

        if zoom:
            f |= pygame.SCALED

        self.window = pygame.display.set_mode((self.screen_width, self.screen_height), flags=f)
        # in non opengl mode we blit directly on the screen window
        self.screen = self.window

        if use_opengl:
            # pg.draw on this surface. then this surface is converted into a texture
            # then this texture is sampled2D in the FS and rendered into the screen (which is a 2 triangles  => quad)
            self.display = pygame.Surface((self.screen_width, self.screen_height))
            self.screen = self.display

            # OpenGL context / options
            self.ctx = mgl.create_context()

            self.ctx.enable(flags=mgl.BLEND)

            quad = [
                # pos (x, y), uv coords (x, y)
                -1.0, 1.0, 0.0, 0.0,
                1.0, 1.0, 1.0, 0.0,
                -1.0, -1.0, 0.0, 1.0,
                1.0, -1.0, 1.0, 1.0,
            ]

            quad_buffer = self.ctx.buffer(data=np.array(quad, dtype='f4'))

            self.all_shaders = ShaderProgram(self.ctx)
            self.screen_program = self.all_shaders.get_program("screen")

            self.vao = self.ctx.vertex_array(self.screen_program, [(quad_buffer, '2f 2f', 'vert', 'texcoord')])

            self.frame_tex = self.surf_to_texture(self.display)
            self.frame_tex.use(0)
            self.screen_program['tex'] = 0

            self.ctx.clear(color=(0.0, 0.0, 0.0))

            if show_options:
                imgui.create_context()
                self.imgui_renderer = pygame_imgui.PygameRenderer()
                imgui.get_io().display_size = self.screen_width, self.screen_height
        
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

    def getv(self, name, current_level=6):
        return getattr(self, "%s_%s" % (name, str(current_level)))

    def surf_to_texture(self, surf):
        tex = self.ctx.texture(surf.get_size(), 4)
        tex.filter = (mgl.NEAREST, mgl.NEAREST)
        tex.swizzle = 'BGRA'
        # tex.write(surf.get_view('1'))
        return tex
    
    def set_uniform(self, program, u_name, u_value):
        try:
            program[u_name] = u_value
        except KeyError:
            pass


# -------------------------------------------------------------------------------------------------

class Action(str, enum.Enum):

    PLAY        = enum.auto()
    LOGIN_OK    = enum.auto()
    LOGIN_DENY  = enum.auto()
    LOGIN       = enum.auto()
    EXITED      = enum.auto()

    PLAYER_UPDATE = enum.auto()
    PLAYER_UPDATE_REQUEST = enum.auto()

    OTHER_PLAYER_UPDATE = enum.auto()

# -------------------------------------------------------------------------------------------------

class GameClientProtocol(WebSocketClientProtocol):

    def onOpen(self):
        print("Connected to the GameServer, username=%s" % self.factory.player_name)

        msg = {"a":Action.LOGIN, "p":self.factory.player_name}

        if USE_JSON:
            self.sendMessage(json.dumps(msg).encode('utf8'))
        else:
            self.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)

    def onMessage(self, payload, isBinary):

        if isBinary:
            r = msgpack.unpackb(payload, raw=False)
        else:
            #print("Message received: %s" % payload.decode('utf8'))
            r = json.loads(payload.decode('utf8'))

        if r["a"] == Action.LOGIN_OK:
            print("Entered in the game as ship n°%s" % r["p"])
            self.factory.ship_number = str(r["p"]) # we are ship #x in the game
            self.factory._state = Action.PLAY

        elif r["a"] == Action.LOGIN_DENY:
            print("Failed to enter in the game: %s"  % r["p"])
            # TODO retry

        elif r["a"] == Action.PLAYER_UPDATE_REQUEST:
            #print("Player update requested, sending player update...")

            # { "ship_number":"3", "player_name":"tony, "level":"6", "xpos":"412", "ypos":"517", "angle":"250", "tp":"True", "sp":"False", "shots":[(x,y), (x2, y2), ...] }
            ship_update = { "ship_number":self.factory.ship_number, "player_name":self.factory.player_name, "level":self.factory.level,
                            "xpos":self.factory.xpos, "ypos":self.factory.ypos, "angle":self.factory.angle, "landed":self.factory.landed,
                            "tp":self.factory.tp, "sp":self.factory.sp, "shots":self.factory.shots, "game_over":self.factory.game_over}
            
            msg = {"a" : Action.PLAYER_UPDATE, "p":ship_update}
            
            if USE_JSON:
                self.sendMessage(json.dumps(msg).encode('utf8'))
            else:
                self.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)

            if self.factory.game_over:
                #print("Game Over, disconnecting...")
                reactor.callLater(5, self.dropConnection, abort=True)

        elif r["a"] == Action.OTHER_PLAYER_UPDATE:
            #print("Received another player update: ", r["p"])

            ship_update = r["p"]
            setattr(self.factory, "other_player_%s" % ship_update["ship_number"], ship_update)

    def onClose(self, wasClean, code, reason):
        print("Exited from the GameServer")
        self.factory._state = Action.EXITED

# -------------------------------------------------------------------------------------------------

#class GameClientFactory(WebSocketClientFactory, ReconnectingClientFactory):
class GameClientFactory(WebSocketClientFactory):

    def __init__(self, url):
        WebSocketClientFactory.__init__(self, url)
        #ReconnectingClientFactory.__init__(self)

        self._state = Action.LOGIN

        self.player_name = ""
        
        #{ ship_number: 1, "player_name":"tony", "level":"6", "xpos":"412", "ypos":"517", "angle":"250", "tp":"True", "sp":"False", landed, "shots":[(x,y), (x2, y2), ...]} }
        self.ship_number = "1"
        self.level = 6
        self.xpos = 0
        self.ypos = 0
        self.angle = 0
        self.tp = False
        self.sp = False
        self.landed = True
        self.shots = []
        self.game_over = False

    #def clientConnectionFailed(self, connector, reason):
    #    print("Client connection failed .. retrying ..")
    #    self.retry(connector)

    #def clientConnectionLost(self, connector, reason):
    #    print("Client connection lost .. retrying ..")
    #    self.retry(connector)

# -------------------------------------------------------------------------------------------------

class GameMenu():
    
    def __init__(self, user_settings=None):

        if user_settings:
            default_username = user_settings["player_name"]
            default_server_url = user_settings["server"]

            default_ship_input = user_settings["ship_control"]
            if default_ship_input == "k1":
                default_ship_input = 0
            elif default_ship_input == "k2":
                default_ship_input = 1
            elif default_ship_input == "j1":
                default_ship_input = 2

            default_sap = user_settings["show_all_players"]
            if default_sap:
                default_sap = 0
            else:
                default_sap = 1

            default_opengl = user_settings["opengl"]
            if default_opengl:
                default_opengl = 0
            else:
                default_opengl = 1

            default_zoom = user_settings["zoom"]
            if default_zoom:
                default_zoom = 1
            else:
                default_zoom = 0

            default_show_options = user_settings["show_options"]
            if default_show_options:
                default_show_options = 1
            else:
                default_show_options = 0

        # no settings file yet
        else:
            default_username = "prn"
            default_server_url = "None"
            default_ship_input = 0
            default_sap = 0
            default_opengl = 0
            default_zoom = 0
            default_show_options = 0

        self.menu_surface = pygame.display.set_mode((320*3, 256*3))

        self.background_image = pygame_menu.BaseImage(drawing_mode=pygame_menu.baseimage.IMAGE_MODE_FILL,
                                image_path=os.path.join(os.path.dirname(__file__), "assets", "wiki", "mayhem_menu%s.png" % str(randint(0, 1)))
        )
        #self.background_image.set_alpha(255)

        theme = pygame_menu.themes.THEME_DARK
        theme.background_color = (0, 0, 0, 210)
        theme.title_bar_style = pygame_menu.widgets.MENUBAR_STYLE_NONE

        self.menu = pygame_menu.Menu(
            width=(320*3)*0.8, height=(256*3)*0.8, title="",
            theme=theme
        )

        self.menu.add.button('PLAY', self.start_game)

        self.user_name = self.menu.add.text_input('Name: ', default=default_username, maxchar=16)
        self.menu.add.selector('Inputs: ', [('Keyboard 1', 'k1'), ('Keyboard 2', 'k2'), ('Joystick', 'j1')], 
                               default=default_ship_input, selector_id="ship_control", onchange=self.set_ship_control)
        
        self.menu.add.selector('Show all players: ', [('ON', True), ('OFF', False)], default=default_sap, 
                               selector_id="show_all_players", onchange=self.set_show_all_players)
        self.menu.add.selector('OpenGL: ', [('ON', True), ('OFF', False)], default=default_opengl, 
                               selector_id="opengl", onchange=self.set_opengl)
        self.menu.add.selector('Zoom: ', [('OFF', False), ('ON', True)], default=default_zoom, 
                               selector_id="zoom", onchange=self.set_zoom)
        self.menu.add.selector('Show options: ', [('OFF', False), ('ON', True)], default=default_show_options, 
                               selector_id="show_options", onchange=self.set_show_options)
        
        self.server_url = self.menu.add.text_input('Server: ', default=default_server_url)

        self.menu.add.button('Quit', pygame_menu.events.EXIT)

        self.clock = pygame.time.Clock()
        self.menu_loop = True

        # game params
        self.ship_control = 'k1'
        self.show_all_players = True

    def set_opengl(self, selected, value):
        self.opengl = value
    def set_zoom(self, selected, value):
        self.zoom = value
    def set_show_options(self, selected, value):
        self.show_options = value
    def set_show_all_players(self, selected, value):
        self.show_all_players = value
    def set_ship_control(self, selected, value):
        self.ship_control = value

    def start_game(self):
        self.player_name = self.user_name.get_value()
        self.server = self.server_url.get_value()
        self.ship_control = self.menu.get_widget("ship_control").get_value()[0][1]
        self.show_all_players = self.menu.get_widget("show_all_players").get_value()[0][1]
        self.show_options = self.menu.get_widget("show_options").get_value()[0][1]
        self.opengl = self.menu.get_widget("opengl").get_value()[0][1]
        self.zoom = self.menu.get_widget("zoom").get_value()[0][1]
        
        self.menu_loop = False

    def loop(self):

        while self.menu_loop:

            events = pygame.event.get()
            for event in events:

                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    sys.exit(0)

            self.menu.update(events)
            self.background_image.draw(self.menu_surface)
            self.menu.draw(self.menu_surface)

            pygame.display.flip()
            self.clock.tick(60)

# -------------------------------------------------------------------------------------------------

def run():
    #pygame.mixer.pre_init(frequency=22050)
    pygame.init()
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    #pygame.display.init()

    pygame.mouse.set_visible(True)
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
    parser.add_argument('-fps', '--fps', help='', type=int, action="store", default=60)
    parser.add_argument('-dp', '--debug_print', help='', action="store", default=False)

    parser.add_argument('-m', '--motion', help='How the ship moves', action="store", default='gravity', choices=("basic", "thrust", "gravity"))
    parser.add_argument('-r', '--record_play', help='', action="store", default="")
    parser.add_argument('-pr', '--play_recorded', help='', action="store", default="")

    parser.add_argument('-server', '--server', help='', action="store", default="")
    parser.add_argument('-pn', '--player_name', help='', action="store", default="tony")
    parser.add_argument('-sap', '--show_all_players', help='', action="store_true", default=False)
    parser.add_argument('-sc', '--ship_control', help='ship control', action="store", default='k1', choices=("k1", "k2", "j1", "j2"))

    parser.add_argument('-zoom', '--zoom', help='', action="store_true", default=False)
    parser.add_argument('-opengl', '--opengl', help='', action="store_false", default=True)
    parser.add_argument('-show_options', '--show_options', help='', action="store_true", default=False)

    result = parser.parse_args()
    args = dict(result._get_kwargs())

    print("Args=", args)

    if USE_JSON:
        print("WARN: Using json, if the server is using msgpack you would need to install it")
    else:
        print("Using msgpack")

    # player vars from command line
    player_name = args["player_name"]
    ship_control = args["ship_control"]
    show_all_players = args["show_all_players"]
    server = args["server"]
    fps = args["fps"]
    level = 6
    opengl = args["opengl"]
    zoom = args["zoom"]
    show_options = args["show_options"]

    # GameMenu (player vars from menu)

    # load previous user settings
    user_settings_file = os.path.join(os.path.dirname(__file__), "user_settings.dat")

    if os.path.exists(user_settings_file):
        with open(user_settings_file, "rb") as f:
            user_settings = pickle.load(f)
    else:
        user_settings = {}
    
    print("user_settings loaded", user_settings)

    gm = GameMenu(user_settings)
    gm.loop()

    # assign values for our Mayhem env
    player_name = gm.player_name
    ship_control = gm.ship_control
    show_all_players = gm.show_all_players
    server = gm.server
    opengl = gm.opengl
    zoom = gm.zoom
    show_options = gm.show_options

    # dump user settings
    user_settings = {"player_name":player_name, "ship_control":ship_control,"show_all_players":show_all_players, 
                        "server":server, "opengl":opengl, "zoom":zoom, "show_options":show_options}
    print("user_settings saved", user_settings)
    with open(user_settings_file, "wb") as f:
        pickle.dump(user_settings, f, protocol=pickle.HIGHEST_PROTOCOL)

    # trying fixed "nice looking" width/height
    if show_all_players:
        width  = 704*2
        height = 448*2
    else:
        width  = 704
        height = 448

    # online ?
    if server and server!="None":
        print("Going to connect to %s" % server)
        game_client_factory = GameClientFactory(server)
        game_client_factory.protocol = GameClientProtocol
        connectWS(game_client_factory)
    else:
        game_client_factory = None
        show_all_players = True

    # game env
    game_window = GameWindow(width, height, zoom=zoom, use_opengl=opengl, show_options=show_options)

    game_env = MayhemEnv(game_window, level=level, max_fps=fps, debug_print=args["debug_print"], motion=args["motion"],
                    record_play=args["record_play"], play_recorded=args["play_recorded"], player_name=player_name, 
                    show_all_players=show_all_players, ship_control=ship_control, game_client_factory=game_client_factory)

    # pygame loop
    #while True:
    #    game_env.game_loop()

    # twisted loop
    tick = task.LoopingCall(game_env.game_loop)
    tick.start(1.0 / int(args["fps"]))

    reactor.run()

# -------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    run()
