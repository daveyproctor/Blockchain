import json
import secrets
import hashlib
import time
import pickle
import itertools
import sys, socket, select
import threading

import logging
logging.basicConfig(level=logging.DEBUG)



'''
Block
'''
class Block(object):


    '''
    ___init___

    initialize a block

    - { int } index  - the block index in the chain
    - { str } parent - the hash of the parent block
    - { str } data   - the data to be inserted into the block

    returns None (implicit object return)
    '''
    def __init__( self, index, parent_hash, data ):
        self.index       = index
        self.parent_hash = parent_hash
        self.data        = data  # NB: You're welcome to put anything or nothing into the chain.

        self.hashed      = False

        self.max_nonce = 2 ** 32 # 4 billion


    '''
    hash

    (Try to) mine a (valid) hash for the block

    - { int } difficulty - the difficulty to be met, from the network

    returns String
    '''
    def search_hash( self, difficulty, startSearch=0, steps=None):
        # Implements hashing of block until difficulty is exceeded.
        # Use the SHA256 hash function (from hashlib library).
        # The hash should be over the index, hash of parent, a unix epoch timestamp in elapsed seconds (time.time()), a random nonce (from secrets library) and the data.
        # We will refer to all of these contents except the data as a "header".
        # We store and use the hex representation of the hash, from hash.hexdigest().
        #
        # "[U]ntil difficulty is exceeded" means at least the specified number of leading zeros are present in the hash as the "proof of work." 
        # We keep hashing with different nonces till you get one that works.

        self.timestamp = time.time()
        self.nonce     = '{ some nonce }'
        self.hash      = '{ some hash }'

        """https://gist.github.com/scharton/102100f39fa9c8a9b55330a507a5590f"""

        # calculate the difficulty target
        target = 2 ** (256-difficulty)
        if steps is not None:
            max_nonce = min(self.max_nonce, startSearch + steps)
        else:
            max_nonce = self.max_nonce

        header = str(self.index) + str(self.parent_hash) + str(self.data)

        for nonce in range(startSearch, max_nonce):
            self.timestamp = time.time()
            hash_result = hashlib.sha256((str(header)+str(self.timestamp)+str(nonce)).encode()).hexdigest()

            # check if this is a valid result, below the target
            if int(hash_result, 16) < target:
                self.hash = hash_result
                self.nonce = nonce
                self.hashed = True
                return self.hash 

        return None

    '''
    serialize

    serialize the block into a format for sharing over the wire

    returns String or Bytes
    '''
    def serialize( self ):
        return pickle.dumps(self)


    '''
    deserialize

    deserialize the block from the wire and store

    returns Block object
    '''
    def deserialize( block_repr ):
        return pickle.loads(block_repr)

    '''
    __str__

    string representation of the block for printing

    returns String
    '''
    def __str__( self ):
        return "Block {}. Hash:{}".format(self.index, self.hash)

'''
Blockchain
'''
class Blockchain(object):


    '''
    ___init___

    initialize the blockchain network

    - { int } difficulty - the proof of work difficulty in the network

    returns None (implicit object return)
    '''
    def __init__(self, difficulty):
        self.chain      = []
        self.difficulty = difficulty

    '''
    add_block

    add a block to the chain

    - { Block } block - block to add

    returns Bool
    '''
    def add_block( self, block ):
        # if genesis block, just add directly
        if len( self.chain ) == 0 and block.index == 0:
            if self.validate( block, "No_parent"):
                self.chain.append( block )
                return True
            return False

        # check that new block is valid and child of current head of the chain
        if self.validate( block, self.chain[ -1 ] ):
            self.chain.append( block )
            return True
        return False


    '''
    validate

    validate the correctness of a block
    assume parent is legitimate

    - { Block } block  - block to be checked
    - { Block } parent - parent block to be checked against

    returns Bool
    '''
    def validate( self, block, parent ):
        #   2.,3. Valid hash
        if block.hashed == False:
            return False
        header = str(block.index) + str(block.parent_hash) + str(block.data)
        hash_result = hashlib.sha256((str(header)+str(block.timestamp)+str(block.nonce)).encode()).hexdigest()
        if hash_result != block.hash:
            return False
        # Check difficulty
        target = 2 ** (256-self.difficulty)
        if int(hash_result, 16) >= target:
            return False

        # Genesis block? if so, done.
        if block.index == 0 and parent == "No_parent":
            # Genesis block
            return True

        #   1.,4.,5. Parent-child relationship
        if block.timestamp < parent.timestamp:
            return False
        if parent.index + 1 != block.index:
            return False
        if block.parent_hash != parent.hash:
            return False

        return True

    '''
    validate_chain

    validate the correctness of the full chain

    returns Bool
    '''
    def validate_chain( self ):
        if len(self.chain) == 0:
            logging.info("validate_chain called on zero-length chain")
            return True
        if self.validate(self.chain[0], "No_parent") == False:
            return False
        for i, block in enumerate(self.chain[1:]):
            if self.validate(block, self.chain[i]) == False:
                return False
        return True

    '''
    __str__

    string representation of the full chain for printing

    returns String
    '''
    def __str__( self ):
        sc = '\nNo. of Blocks: {l}\n'.format( l = len( self.chain ) )

        offset = len( str( len( self.chain ) ) )
        for i, block in enumerate( self.chain ):
            sc += '\tBlock {n}. {h}\n'.format( n = str( i ).rjust( offset ), h = str( block ) )

        sc += '\n'

        return sc

'''
DistributedBlockchain
'''
class DistributedBlockchain(Blockchain):

    def __init__(self, difficulty, whoami):
        # Inherited class
        Blockchain.__init__(self, difficulty)

        # If true, don't supress exceptions
        self.DEBUG = True

        # Network information
        self.whoami = whoami
        self.directory = [
            { 'ip' : None, 'port' : None }
        ]
        # communcation list. Don't need to know metadata per socket because
        # all peer nodes are symmetric
        self.sockets = set()
        # track who's serving over which ports
        self.ports = {}

        # Concurrency
        self.lock = threading.Lock()

    '''
    serialize

    serialize the chain into a transportable format

    returns String or Bytes
    '''
    def serialize_chain( self ):
        with self.lock:
            return pickle.dumps(self.chain)

    '''
    deserialize

    deserialize the chain, potentially from over the wire.

    returns None
    '''
    def deserialize_chain(self, chain_repr):
        with self.lock:
            self.chain = pickle.loads(chain_repr)

    '''
    _generate
    
    generate (mine) just one new block

    concurrent with new blocks coming in; 
    doesn't hold a grudge if lost lottery this go-round
    
    input: steps to run hashing process before polling new block
    this parameter could be fine-tuned for max profit by individual based on
    how fast his computer is vs. number of peers

    side effect: add Block to chain (even after others beat me to it);

    output: new Block
    '''
    def _generate(self, numSteps=100):
        if len(self.chain) == 0:
            raise RuntimeError("Call genesis for the first block")
            
        newBlock = None
        while newBlock is None:
            with self.lock:
                parentBlock = self.chain[-1]
            index = parentBlock.index+1
            data = "Data for block {}".format(index)
            newBlock = Block(index, parentBlock.hash, data)
            for startSearch in range(0, newBlock.max_nonce, numSteps):
                block_hash = newBlock.search_hash(self.difficulty, startSearch, numSteps)
                if index != len(self.chain):
                    # new block has arrived, start from tip of trunk again
                    # Even if we just found one, we'll yield
                    logging.info("{}: Restart mining cycle due to received block".format(self.whoami))
                    newBlock = None
                    break
                elif block_hash is not None:
                    # Found block
                    # Would like to pick up a communication lock here; 
                    # obviously that's impossible for internet latency
                    # and incentive reasons, so forks are possible even
                    # among cooperative parties due to this race condition.
                    break
                elif block_hash is None:
                    continue

        if self.add_block(newBlock) == False:
            logging.error("{}: Networked race condition or weirdness in mining process".format(self.whoami))
            return None
        logging.info("{}: Generated {}".format(self.whoami, str(newBlock)))
        return newBlock
    
    '''
    genesis
    
    generate (mine) the genesis block
    input: None
    side effect: add block 
    
    returns Block
    '''
    def _genesis(self):
        genesis = Block( 0, '0', 'Genesis Block' )
        if genesis.search_hash( self.difficulty ) is None:
            logging.error("{}: Failed chain genesis".format(self.whoami))
            return None
    
        if self.add_block(genesis) == False:
            logging.error("{}: Networked race condition or weirdness in mining process".format(self.whoami))
            return None
        logging.info("{}: Genesis {}".format(self.whoami, str(genesis)))
        return genesis

    '''
    _generate and also broadcast
    '''
    def generate(self):
        self.broadcast_block(self._generate())

    '''
    _genesis and also broadcast
    '''
    def genesis(self):
        self.broadcast_block(self._genesis())

    '''
    add_node

    add a new node to the directory

    returns None
    '''
    def add_node( self, ip, port ):
        with self.lock:
            self.directory.append( { 'ip' : ip, 'port' : port } )

    def add_client_socket(self, socket):
        with self.lock:
            self.sockets.add(socket)

    def remove_client_socket(self, socket):
        with self.lock:
            self.sockets.remove(socket)

    def set_node_port(self, node, port):
        with self.lock:
            self.ports[node] = port

    def get_node_port(self, node):
        with self.lock:
            return self.ports[node]

    '''
    broadcast_block
    
    broadcast mined block to network
    
    input: block
    output: none
    '''
    def broadcast_block(self, block):
        self.broadcast(pickle.dumps({"type": "Block", "val": block.serialize()}))
        logging.info("{}: Broadcast {}".format(self.whoami, str(block)))

    def broadcast_chain(self):
        self.broadcast(pickle.dumps({"type": "Chain", "val": self.serialize_chain()}))
        logging.info("{}: Broadcast blockchain: {}".format(self.whoami, str(self)))

    def broadcast_request_chain(self):
        self.broadcast(pickle.dumps({"type": "Request_chain"}))

    def broadcast(self, data):
        _,ready_to_write,_ = select.select([],list(self.sockets),[])
        logging.info("{}: Broadcasting type {} message to {} peers".format(self.whoami, pickle.loads(data)["type"], len(ready_to_write)))
        for sock in ready_to_write:
            sock.send(data)

    def listen(self):
        """
        (Always) listen for whatever people tell me and handle appropriately
        Inline comments.
        """
        while 1:
            logging.info("{}: Start listen cycle".format(self.whoami))
            ready_to_read,_,_ = select.select(list(self.sockets),[],[])
            for sock in ready_to_read:
                data = sock.recv(RECV_BUFFER)
                if not data:
                    logging.info('{}: Disconnected from server'.format(self.whoami))
                    self.remove_client_socket(sock)
                else:
                    logging.info('{}: Received data'.format(self.whoami))
                    data = pickle.loads(data)
                    try:
                        if data["type"] == "Block":
                            '''
                            previously listen_broadcast
                            
                            listen for broadcasts of new blocks
                            
                            side effect: adds new block to chain if valid
                            '''
                            block = Block.deserialize(data["val"])
                            if len(self.chain) == 0:
                                if self.validate(block, "No_parent"):
                                    # Received genesis
                                    self.add_block(block)
                                    logging.info("{}: received genesis".format(self.whoami))
                            elif self.validate(block, chain[-1]):
                                self.add_block(block)
                                logging.info("{}: received valid new block", self.whoami)
                            elif block.index > chain[-1].index + 1:
                                # Failed to validate it, but we could just be missing tip of trunk
                                # Consider broadcast_request_chain
                                logging.info("{}: Seemingly lagging behind longer chains".format(self.whoami))
                            else:
                                logging.info("{}: Received bogus block".format(self.whoami))

                        elif data["type"] == "Chain":
                            '''
                            previously query_chain
                            
                            query the current status of the chain
                            
                            side effect: resets our chain to longest valid chain
                            '''
                            proposed_bchain = DistributedBlockchain(self.difficulty, "Annonymous")
                            proposed_bchain.deserialize_chain(data["val"])
                            if len(self.chain)<len(proposed_bchain.chain) and proposed_bchain.validate_chain():
                                # Accept new chain
                                logging.info("{}: received longer than current chain {}".format(self.whoami, proposed_bchain.serialize_chain()))
                                self.chain = proposed_bchain.chain
                            else:
                                logging.info("{}: received chain that's not both valid+longer than current; disgarding".format(self.whoami, proposed_bchain.serialize_chain()))

                        elif data["type"] == "Request_chain":
                            '''
                            previously listen_query
                            
                            listen for requests for current chain status
                            '''
                            self.broadcast_chain()
                        else:
                            raise RuntimeError("Bogus reception")

                    except Exception as e:
                        logging.info("{}: Bogus reception")
                        if self.DEBUG:
                            raise e
            assert self.validate_chain()

    def serverDispatch(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, bchain.get_node_port(self.whoami)))
        server_socket.listen(5)
        while 1:
            # This blocks (hangs) in an efficient way even after all connections made
            ready_to_read,ready_to_write,in_error = select.select([server_socket],[],[])
            if server_socket in ready_to_read:
                # a new connection request recieved
                s, addr = server_socket.accept()
                self.add_client_socket(s)
                logging.info("{}: Client ({}, {}) connected".format(self.whoami, addr[0], addr[1]))
            else:
                logging.error("{}: Failed would-be initial connection".format(self.whoami))
          
    def clientTryConnect(self):
        # protocol for who's serving me in the initial connection
        servers = set(peer1 for peer1, peer2 in itertools.combinations(allNodes, 2) if peer2==self.whoami)
        printedSet = set()
        while len(servers) > 0:
            for peer in servers:
                # I'll be the client
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                try:
                    s.connect((HOST, bchain.get_node_port(peer)))
                    bchain.add_client_socket(s)
                    
                    logging.info("{}: Connected to {}".format(self.whoami, peer))
                    self.add_node("localhost", self.get_node_port(peer))
                    servers.remove(peer)
                    break
                except ConnectionRefusedError:
                    if peer not in printedSet:
                        logging.info('{}: {} is not online'.format(self.whoami, peer))
                        printedSet.add(peer)
                    time.sleep(1)
        logging.info("{}: All client-outreach connections made".format(self.whoami))

HOST = 'localhost'
RECV_BUFFER = 4096 
PORT_MIN = 8000
allNodes = ("generator", "honest", "dishonest", "joiner")

if __name__ == '__main__':

    if (len(sys.argv) != 2):
        print('Usage : python blockchain.py [{}]'.format(" | ".join(allNodes)))
        sys.exit()

    bchain = DistributedBlockchain( difficulty=16, whoami=sys.argv[1] )

    # track who's serving over which ports
    for i, node in enumerate(allNodes):
        bchain.set_node_port(node, PORT_MIN+i)

    # Start server for those trying to connect to me
    x = threading.Thread(target=bchain.serverDispatch)
    x.start()

    # Try connect to peers
    y = threading.Thread(target=bchain.clientTryConnect)
    y.start()

    # # Give everyone time to come online
    time.sleep(10)

    # Efficient listen for peers
    z = threading.Thread(target=bchain.listen)
    z.start()

    if bchain.whoami == "generator":
        # Auto-broadcasts
        bchain.genesis()
        # print(bchain)
    elif bchain.whoami == "honest":
        # while len(bchain.chain) == 0:
        #     # Let generator go first to be nice
        #     pass
        bchain.broadcast_request_chain()
        # time.sleep(5)
        # print(bchain)
        # Auto-broadcasts
        # bchain.generate()




