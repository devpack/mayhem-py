import sys, json, threading, enum, queue, argparse

from twisted.internet import reactor
from twisted.internet import task
from twisted.python import log

from autobahn.exception import Disconnected
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol, listenWS

try:
    import msgpack
    USE_JSON = False
except:
    USE_JSON = True

DEBUG_PRINT = 0

# -------------------------------------------------------------------------------------------------

from functools import wraps

def synchronized( tlockname ):
    """A decorator to place an instance based lock around a method """

    def _synched(func):
        @wraps(func)
        def _synchronizer(self,*args, **kwargs):
            tlock = self.__getattribute__( tlockname)
 
            # if tlock is None this means the tlockname match no class arg or is None
            if tlock:
                #print "AQUIRING " + tlockname
                tlock.acquire()
                #print "AQUIRED " + tlockname
            try:
                return func(self, *args, **kwargs)
            finally:
                if tlock:
                    #print "RELEASING " + tlockname
                    tlock.release()
                    #print "RELEASED " + tlockname
        return _synchronizer
    return _synched

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

    SERVER_STAT_REGISTER = enum.auto()
    SERVER_STAT_OK = enum.auto()
    SERVER_STAT_UPDATE = enum.auto()

# -------------------------------------------------------------------------------------------------

class PlayerProtocol(WebSocketServerProtocol):

    def __init__(self):
        super().__init__()

        self.room_id = None
        self.ship_nb = None

    def onOpen(self):
        print(f"Player {self.peer} connected")

        self.packet_queue = queue.Queue()
        self._state = self.NOP # used only to get the server state
        
    # a player quits, we remove it
    def onClose(self, wasClean, code, reason):
        self.factory.del_player(self)
        # TODO send disconnet packet to the players

    # message received from a player 
    def onMessage(self, payload, isBinary):

        if isBinary:
            msg = msgpack.unpackb(payload, raw=False)
        else:
            msg = json.loads(payload.decode('utf8'))

        if DEBUG_PRINT:
            print("Received action=%s, payload=%s, from: %s" % (Action(msg["a"]), msg["p"], self.peer))

        # A player wants to connect, we add it here to the player list 
        #     so that tick() can be called for this player
        if msg["a"] == Action.LOGIN:

            p = msg["p"]
            try:
                self.room_id = int(p["room_id"])
            except:
                try:
                    self.room_id = p["room_id"]
                except:
                    pass
            
            # 0, "", None means give me the first room where there is space
            #   this is done by setting self.room_id to None
            if self.room_id in (0, "0", "", "None", "none"):
                self.room_id = None

            print("room_id=", self.room_id)

            success = self.factory.add_player(self)
            if success:
                self._state = self.PLAY

        elif msg["a"] == Action.SERVER_STAT_REGISTER:
            self.factory.add_watcher(self)

            msg = {"a":Action.SERVER_STAT_OK, "p":""}
            if USE_JSON:
                self.sendMessage(json.dumps(msg).encode('utf8'))
            else:
                self.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)

        # Other actions are put into the action queue, and going to be processed
        #     into the tick() function
        else:
            self.add_packet(self, msg)

    def add_packet(self, sender, msg):
        self.packet_queue.put((sender, msg))

    def NOP(self, sender, msg):
        pass

    def PLAY(self, sender, msg):
        if DEBUG_PRINT:
            print("PLAY received action=%s, payload=%s, from: %s" % (Action(msg["a"]), msg["p"], sender))

        if msg["a"] == Action.PLAYER_UPDATE:
            # send this player update to all other players
            self.factory.broadcast_msg(sender, msg["p"])

    def tick(self):
        #print("tick called for %s" % self)

        # Process the next packet in the queue
        if not self.packet_queue.empty():
            t = self.packet_queue.get()
            #print(self._state, t)
            self._state(*t)

        if self._state == self.PLAY:
            if DEBUG_PRINT:
                print("Request player update for %s" % self)

            # request player update
            if 1:
                msg = {"a":Action.PLAYER_UPDATE_REQUEST, "p":"PLAYER_UPDATE_REQUEST"}
                try:
                    if USE_JSON:
                        self.sendMessage(json.dumps(msg).encode('utf8'))
                    else:
                        self.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)
                except Disconnected:
                    print("Could not send %s, client disconnected" % msg)

# -------------------------------------------------------------------------------------------------

class GameServerFactory(WebSocketServerFactory):

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)

        # { room_id : {"ships":[1, 2, 3, 4], "players":[{"address":xxx, "ship_nb"}, ...] }
        self.rooms = {}

        self.add_player_lock = threading.Lock()
        self.del_player_lock = threading.Lock()

        tickloop = task.LoopingCall(self.tick)
        tickloop.start(1 / 60.)

        # server status
        self.server_watchers = []

    # server status update
    def server_status_update(self):
        for watcher in self.server_watchers:
                
            msg = {"a":Action.SERVER_STAT_UPDATE, "p":{"state":repr(self.rooms)}}
            try:
                if USE_JSON:
                    watcher.sendMessage(json.dumps(msg).encode('utf8'))
                else:
                    watcher.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)
            except Disconnected:
                print("Could not send %s, watcher disconnected" % msg)

    def add_watcher(self, watcher):
        if watcher not in self.server_watchers:
            self.server_watchers.append(watcher)

        # initial status
        msg = {"a":Action.SERVER_STAT_UPDATE, "p":{"state":repr(self.rooms)}}
        try:
            if USE_JSON:
                watcher.sendMessage(json.dumps(msg).encode('utf8'))
            else:
                watcher.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)
        except Disconnected:
            print("Could not send %s, watcher disconnected" % msg)

    def del_watcher(self, watcher):
        if watcher in self.server_watchers:
            self.server_watchers.remove(watcher)

    # player update
    def tick(self):
        for room_id in self.rooms:
            for player in self.rooms[room_id]["players"]:
                player.tick()

    @synchronized('del_player_lock')
    def del_player(self, player):

        # only a logger player has a room_id (so can be removed)
        if player.room_id:
            try:
                self.rooms[player.room_id]["players"].remove(player)
                self.rooms[player.room_id]["ships"].insert(0, player.ship_nb) # added back new freed ship into the avaible ship list
                self.rooms[player.room_id]["ships"].sort()

                print(f"Removed player {player} (using ship #{player.ship_nb}) from room {player.room_id}")

                # no player left => remove the room
                if not self.rooms[player.room_id]["players"]:
                    del self.rooms[player.room_id]
                    print(f"Room {player.room_id} is empty, remove it")

            except Exception as e:
                print("Failed to remove %s : %s" % (repr(player), repr(e)))
                
            self.server_status_update()

            print("ROOMS=", self.rooms)

    @synchronized('add_player_lock')
    def add_player(self, player):

        print("ROOMS=", self.rooms)

        # requested player.room_id is not None, we find the first room where there is a ship available
        #    if no place left, we create a new room for the new player
        if player.room_id is None:

            print("Player did not request a specific room")

            for a_room in self.rooms:
                if len(self.rooms[a_room]["ships"]) > 0:

                    ship = self.rooms[a_room]["ships"].pop(0) # first ship available in ships list

                    self.rooms[a_room]["players"].append(player)
                    player.room_id = a_room
                    player.ship_nb = ship
                    
                    print(f"Found space left: assigned ship #{ship} in room {a_room} to player {player}")

                    msg = {"a":Action.LOGIN_OK, "p": {"ship_nb":player.ship_nb, "room_id":player.room_id}}
                    try:
                        if USE_JSON:
                            player.sendMessage(json.dumps(msg).encode('utf8'))
                        else:
                            player.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)    
                    except Disconnected:
                        print("Could not send %s, client disconnected" % msg)
                
                    self.server_status_update()
                    print("ROOMS=", self.rooms)
                    return True
                
            # if we are here this means no place left anywhere, we create a new room (id = start from 1 and inc)
            new_room = 1
            while 1:
                if new_room in self.rooms:
                   new_room += 1
                else:
                    break

            # create the room
            print(f"Created room {new_room}")

            self.rooms[new_room] = {"ships":[2, 3, 4], "players":[]}

            # add the player into the room and assign it ship #1
            self.rooms[new_room]["players"].append(player)
            player.room_id = new_room
            player.ship_nb = 1

            print(f"Assigned ship #1 in room {new_room} to player {player}")

            # send login OK to the player and its ship number (1)
            msg = {"a":Action.LOGIN_OK, "p":{"ship_nb":player.ship_nb, "room_id":player.room_id}}
            try:
                if USE_JSON:
                    player.sendMessage(json.dumps(msg).encode('utf8'))
                else:
                    player.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)    
            except Disconnected:
                print("Could not send %s, client disconnected" % msg)
        
            self.server_status_update()
            print("ROOMS=", self.rooms)
            return True
        
        # requested player.room_id is not None => try to find a place in this room
        else:

            # room_id already exists ? yes
            if player.room_id in self.rooms:
                
                # ship available ? yes
                if len(self.rooms[player.room_id]["ships"]) > 0:

                    ship = self.rooms[player.room_id]["ships"].pop(0) # first ship available in ships list

                    self.rooms[player.room_id]["players"].append(player) # TODO .append(player.peer)
                    player.ship_nb = ship
                    
                    print(f"Assigned ship #{ship} in room {player.room_id} to player {player}")

                    msg = {"a":Action.LOGIN_OK, "p":{"ship_nb":player.ship_nb, "room_id":player.room_id}}
                    try:
                        if USE_JSON:
                            player.sendMessage(json.dumps(msg).encode('utf8'))
                        else:
                            player.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)    
                    except Disconnected:
                        print("Could not send %s, client disconnected" % msg)
                
                    self.server_status_update()
                    print("ROOMS=", self.rooms)
                    return True
                
                # no ship left
                else:
                    msg = {"a":Action.LOGIN_DENY, "p":"Room is full"}
                    try:
                        if USE_JSON:
                            player.sendMessage(json.dumps(msg).encode('utf8'))
                        else:
                            player.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)   
                    except Disconnected:
                        print("Could not send %s, client disconnected" % msg)

                    self.server_status_update()
                    print("ROOMS=", self.rooms)
                    return False

            # room_id already exists ? no
            else:
                # create the room
                print(f"Created room {player.room_id}")

                self.rooms[player.room_id] = {"ships":[2, 3, 4], "players":[]}

                # add the player into the room and assign it ship #1
                self.rooms[player.room_id]["players"].append(player)
                player.ship_nb = 1

                print(f"Assigned ship #1 in room {player.room_id} to player {player}")

                # send login OK to the player and its ship number (1)
                msg = {"a":Action.LOGIN_OK, "p":{"ship_nb":player.ship_nb, "room_id":player.room_id}}
                try:
                    if USE_JSON:
                        player.sendMessage(json.dumps(msg).encode('utf8'))
                    else:
                        player.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)    
                except Disconnected:
                    print("Could not send %s, client disconnected" % msg)
            
                self.server_status_update()
                print("ROOMS=", self.rooms)
                return True

    def broadcast_msg(self, from_player, update_payload_from_player):

        for player in self.rooms[from_player.room_id]["players"]:

            if player != from_player:
                msg = {"a":Action.OTHER_PLAYER_UPDATE, "p":update_payload_from_player}
                try:
                    if USE_JSON:
                        player.sendMessage(json.dumps(msg).encode('utf8'))
                    else:
                        player.sendMessage(msgpack.packb(msg, use_bin_type=True), isBinary=True)   
                except Disconnected:
                    print("Could not send %s, client disconnected" % msg)
                    
                if DEBUG_PRINT:
                    print("Sent player update from %s to %s" % (from_player, player))

# -------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    log.startLogging(sys.stdout)

    if USE_JSON:
        print("Using json")
    else:
        print("Using msgpack")

    # options
    parser = argparse.ArgumentParser()

    parser.add_argument('-url', '--url', help='', action="store", default="ws://0.0.0.0:4444")

    result = parser.parse_args()
    args = dict(result._get_kwargs())

    print("Args=", args)

    ServerFactory = GameServerFactory

    factory = ServerFactory(args["url"])
    factory.protocol = PlayerProtocol
    listenWS(factory)

    reactor.run()