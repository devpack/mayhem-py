import sys, json, enum, msgpack

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientFactory, WebSocketClientProtocol, connectWS

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

class GameClientProtocol(WebSocketClientProtocol):

    def onOpen(self):
        print("Connected to the GameServer")

        # login test
        if 0:
            msg = {"a" : Action.LOGIN, "p":{"room_id":3}}
            #msg = {"a" : Action.LOGIN, "p":""}

            #self.sendMessage(json.dumps(msg).encode('utf8'))
            self.sendMessage(msgpack.packb(msg), isBinary=True)

        # server state test
        if 1:
            msg = {"a" : Action.SERVER_STAT_REGISTER, "p":""}
            self.sendMessage(msgpack.packb(msg), isBinary=True)

    def onMessage(self, payload, isBinary):

        if isBinary:

            #r = json.loads(payload.decode('utf8'))
            r =  msgpack.unpackb(payload, raw=False)
            print("Message received: %s" % repr(r))

            if r["a"] == Action.LOGIN_OK:
                print("Entered in the game as ship n°%s" % r["p"])

            elif r["a"] == Action.LOGIN_DENY:
                print("Failed to enter in the game: %s"  % r["p"])

            elif r["a"] == Action.SERVER_STAT_OK:
                print("Watching server stat...")

            elif r["a"] == Action.SERVER_STAT_UPDATE:
                print("Server stat= %s" % r["p"])

            # elif r["a"] == Action.PLAYER_UPDATE_REQUEST:
            #     print("Player update requested, sending player update...")

            #     ship_update = { "ship_number":"3", "player_name":"alex", "level":"6", "xpos":"999", "ypos":"666", "angle":"55", 
            #                     "tp":"True", "sp":"False", "shots":[(500, 500), (600, 600),] }
                
            #     msg = {"a" : Action.PLAYER_UPDATE, "p":ship_update}
            #     self.sendMessage(json.dumps(msg).encode('utf8'))

            elif r["a"] == Action.OTHER_PLAYER_UPDATE:
                print("Received another player update: ", r["p"])
                # todo update player pos in the gameplay

        else:
            print("Message was not binary")

    def onClose(self, wasClean, code, reason):
        print("Exited from the GameServer")
        # TODO reset

# -------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print("Need the WebSocket server address, i.e. ws://127.0.0.1:9000")
        sys.exit(1)

    factory = WebSocketClientFactory(sys.argv[1])
    factory.protocol = GameClientProtocol
    connectWS(factory)

    reactor.run()