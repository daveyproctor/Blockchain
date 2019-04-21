import json
import secrets
import hashlib
import time
import pickle
import itertools
import sys, socket, select
import threading



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
        return self.hash

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
            print("Validate fail test 1")
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
        self.validate(self.chain[0], "No_parent")
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

    def __init__(self, difficulty):
        Blockchain.__init__(self, difficulty)
        self.directory = [
            { 'ip' : None, 'port' : None }
        ]
        # communcation list. Don't need to know metadata per socket because
        # all peer nodes are symmetric
        self.socket_list = []
        # track who's serving over which ports
        self.ports = {}
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
                    print("Restart mining cycle due to received block")
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
            raise RuntimeError("Networked race condition or weirdness in mining process")
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
            raise RuntimeError("Failed chain genesis")
    
        if self.add_block(genesis) == False:
            raise RuntimeError("Networked race condition or weirdness in mining process")
        return genesis

    '''
    _generate and also broadcast
    '''
    def generate():
        self.broadcast(self._generate())

    '''
    _genesis and also broadcast
    '''
    def genesis():
        self.broadcast(self._genesis())

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
            self.socket_list.append(socket)

    def set_node_port(self, node, port):
        with self.lock:
            self.ports[node] = port

    def get_node_port(self, node):
        with self.lock:
            return self.ports[node]

    '''
    broadcast
    
    broadcast mined block to network
    
    input: block
    output: none
    '''
    def broadcast(self, block):
        # Broadcasts newly generated block to all other nodes in the directory.
        for socket in self.socket_list:
            socket.send(block.serialize())
            continue
    
            # TODO: handle exception
            try :
                print(message)
                socket.send(message.encode())
            except Exception as e:
                # broken socket connection
                socket.close()
                # broken socket, remove it
                if socket in SOCKET_LIST:
                    SOCKET_LIST.remove(socket)
                raise(e)
    
    '''
    listen_broadcast
    
    listen for broadcasts of new blocks
    
    input: None
    output: None
    side effect: adds new block to chain if valid
    '''
    def listen_broadcast():
        # TODO: Handle newly broadcast prospective block (i.e. add to chain if valid).
        #       If using HTTP, this should be a route handler.
        pass
    
    '''
    query_chain
    
    query the current status of the chain
    
    TODO: Determine input(s) and output(s).
    '''
    def query_chain():
        # TODO: Request content of chain from all other nodes (using deserialize class method). Keep the majority/plurality (valid) chain.
        pass
    
    '''
    listen_query
    
    list for requests for current chain status
    
    TODO: Determine input(s) and output(s).
    '''
    def listen_query():
        # TODO: Respond to query for contents of full chain (using serialize class method).
        #       If using HTTP, this should be a route handler.
        pass

    def serverDispatch(self, server_socket):
        while 1:
            # Blocks in an efficient way even after all connections made
            ready_to_read,ready_to_write,in_error = select.select([server_socket],[],[])
            if server_socket in ready_to_read:
                # a new connection request recieved
                s, addr = server_socket.accept()
                self.add_client_socket(s)
                print("Client (%s, %s) connected" % addr)
            else:
                print("Odd behavior in server")
          
    def clientTryConnect(self, servers):
        printedSet = set()
        while len(servers) > 0:
            for peer in servers:
                # I'll be the client
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                try:
                    s.connect((HOST, bchain.get_node_port(peer)))
                    bchain.add_client_socket(s)
                    
                    print("Connected to {}".format(peer))
                    self.add_node("localhost", self.get_node_port(peer))
                    servers.remove(peer)
                    break
                except ConnectionRefusedError:
                    if peer not in printedSet:
                        print('{} is not online'.format(peer))
                    printedSet.add(peer)
                    time.sleep(1)
        print("All client-outreach connections made")

HOST = 'localhost'
RECV_BUFFER = 4096 
PORT_MIN = 8000

allNodes = ("generator", "honest", "dishonest", "joiner")

if __name__ == '__main__':

    if (len(sys.argv) != 2):
        print('Usage : python blockchain.py [{}]'.format(" | ".join(allNodes)))
        sys.exit()
    whoami = sys.argv[1]

    bchain = DistributedBlockchain( difficulty=18 )

    # track who's serving over which ports
    for i, node in enumerate(allNodes):
        bchain.set_node_port(node, PORT_MIN+i)

    # start server per node
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, bchain.get_node_port(whoami)))
    server_socket.listen(5)
    x = threading.Thread(target=bchain.serverDispatch, args=(server_socket,))
    x.start()

    # Try connect to peers
    servers = set(peer1 for peer1, peer2 in itertools.combinations(allNodes, 2) if peer2==whoami)
    y = threading.Thread(target=bchain.clientTryConnect, args=(servers,))
    y.start()


    # # Give everyone time to come online
    time.sleep(10)



