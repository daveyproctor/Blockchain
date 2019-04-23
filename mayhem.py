import blockchain
import sys
import time
import threading

import logging
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':

    if (len(sys.argv) != 2):
        print('Usage : python blockchain.py [{}]'.format(" | ".join(blockchain.allNodes)))
        sys.exit()

    bchain = blockchain.DistributedBlockchain( difficulty=16, whoami=sys.argv[1] )

    # track who's serving over which ports
    for i, node in enumerate(blockchain.allNodes):
        bchain.set_node_port(node, blockchain.PORT_MIN+i)

    # Start server for those trying to connect to me
    x = threading.Thread(target=bchain.serverDispatch)
    x.start()

    # Try connect to peers
    y = threading.Thread(target=bchain.clientTryConnect)
    y.start()

    # # Give everyone time to come online
    time.sleep(2)

    # Efficient listen for peers
    z = threading.Thread(target=bchain.listen)
    z.start()

    time.sleep(2)

    if bchain.whoami == "generator":
        bchain.genesis()

    time.sleep(2)

    g = threading.Thread(target=bchain.generate)
    g.start()

