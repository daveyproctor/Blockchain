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

    BEAT = 5
    # # Give everyone time to come online
    time.sleep(2*BEAT)

    # Efficient listen for peers
    z = threading.Thread(target=bchain.listen)
    z.start()

    logging.info("==== a. The generator node mines the genesis block and broadcasts it to the honest and dishonest nodes. ====")
    if bchain.whoami == "generator":
        # Auto-broadcasts
        bchain.genesis()
    elif bchain.whoami == "honest":
        pass
    elif bchain.whoami == "dishonest":
        pass

    time.sleep(BEAT)
    assert(len(bchain.chain) == 1)
    assert(bchain.validate_chain())
    logging.info("{}: Current blockchain: {}".format(bchain.whoami, str(bchain)))
    time.sleep(BEAT)

    logging.info("==== b. The honest node mines a block and broadcasts it to the generator and dishonest nodes. ====")
    if bchain.whoami == "generator":
        pass
    elif bchain.whoami == "honest":
        bchain.generate()
    elif bchain.whoami == "dishonest":
        pass

    time.sleep(BEAT)
    assert(len(bchain.chain) == 2)
    assert(bchain.validate_chain())
    logging.info("{}: Current blockchain: {}".format(bchain.whoami, str(bchain)))
    time.sleep(BEAT)

    logging.info("==== The dishonest node ignores it ====")
    if bchain.whoami == "dishonest":
        bchain.chain.pop()
    time.sleep(BEAT)
    logging.info("{}: Current blockchain: {}".format(bchain.whoami, str(bchain)))
    time.sleep(BEAT)

    logging.info("==== Having ignored the honest's block, the dishonest node mines a block and sends it to the generator and honest nodes, which reject it. ====")
    if bchain.whoami == "dishonest":
        bchain.generate()
    # Note: see listen() for why automatically the other nodes will reject my block
    time.sleep(BEAT)
    logging.info("{}: Current blockchain: {}".format(bchain.whoami, str(bchain)))
    time.sleep(BEAT)



