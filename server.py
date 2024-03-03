import sys, json, threading, enum, queue

from twisted.internet import reactor
from twisted.internet import task

from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol, listenWS

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

# -------------------------------------------------------------------------------------------------

class GameServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        print(f"Player {self.peer} connected")

        self.packet_queue = queue.Queue()
        self._state = self.NOP
        
    # a player quits, we remove it
    def onClose(self, wasClean, code, reason):
        self.factory.del_player(self)
        # TODO send disconnet packet to the players

    # message received from a player 
    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Message was binary")
        else:
            msg = json.loads(payload.decode('utf8'))

            if DEBUG_PRINT:
                print("Received action=%s, payload=%s, from: %s" % (Action(msg["a"]), msg["p"], self.peer))

            # A player wants to connect, we add it here to the player list 
            #     so that tick() can be called for this player
            if msg["a"] == Action.LOGIN:
                success = self.factory.add_player(self)
                if success:
                    self._state = self.PLAY
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
            msg = {"a":Action.PLAYER_UPDATE_REQUEST, "p":"PLAYER_UPDATE_REQUEST"}
            self.sendMessage(json.dumps(msg).encode('utf8')) # we send bytes

# -------------------------------------------------------------------------------------------------

PL_ADDR = 0
SHIP_NB = 1

class GameServerFactory(WebSocketServerFactory):

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)

        self.players = []
        self.ships = [1, 2, 3, 4]
        self.add_player_lock = threading.Lock()

        # how many ticks per second
        self.tickrate = 60
        self.total_ticks = 0
        tickloop = task.LoopingCall(self.tick)
        tickloop.start(1 / self.tickrate)

    def tick(self):
        #print("players=", self.players)

        for pl in self.players:
            pl[PL_ADDR].tick()

    def del_player(self, player):

        for i, pl in enumerate(self.players):
            if pl[PL_ADDR] == player:
                self.ships.insert(0, pl[SHIP_NB]) # added back new freed ship into the avaible ship list
                self.ships.sort()

                self.players.pop(i)
                print("Removed player:%s (%s)" % (i, player.peer ))
                print("Available ships:", self.ships)

    @synchronized('add_player_lock')
    def add_player(self, player):

        print("Available ships:", self.ships)

        already_in = False
        for pl in self.players:
            if pl[PL_ADDR] == player:
                already_in = True
                break

        # player not already logged
        if not already_in:

            # any ship left for this room ? (TODO more room)
            if len(self.ships) > 0:

                ship = self.ships.pop(0)
                print("Added player %s for ship %s" % (player.peer, str(ship)))
                self.players.append( (player, ship) )

                msg = {"a":Action.LOGIN_OK, "p":ship}
                player.sendMessage(json.dumps(msg).encode('utf8')) # we send bytes

                return True
            else:
                msg = {"a":Action.LOGIN_DENY, "p":"Room is full"}
                player.sendMessage(json.dumps(msg).encode('utf8')) # we send bytes

                return False
        else:
            print("Player %s already registered" % player.peer)

            msg = {"a":Action.LOGIN_DENY, "p":"Player already registered"}
            player.sendMessage(json.dumps(msg).encode('utf8'))

            return False
            
    def broadcast_msg(self, from_player, update_payload_from_player):

        for pl in self.players:
            if pl[PL_ADDR] != from_player:
                msg = {"a":Action.OTHER_PLAYER_UPDATE, "p":update_payload_from_player}
                pl[PL_ADDR].sendMessage(json.dumps(msg).encode('utf8'))

                if DEBUG_PRINT:
                    print("Sent player update from %s to %s" % (from_player, pl[PL_ADDR]))

# -------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    log.startLogging(sys.stdout)

    ServerFactory = GameServerFactory

    factory = ServerFactory("ws://0.0.0.0:9000")
    factory.protocol = GameServerProtocol
    listenWS(factory)

    webdir = File(".")
    web = Site(webdir)
    reactor.listenTCP(8080, web)

    reactor.run()