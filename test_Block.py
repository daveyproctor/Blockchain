# Unit tests for Block class of blockchain.py
import blockchain
difficulty=18

block0 = blockchain.Block(0, '0', 'Genesis Block')
block0.search_hash(difficulty)
block1 = blockchain.Block.deserialize(block0.serialize())

assert block0.index == block1.index
assert block0.parent_hash == block1.parent_hash
assert block0.data == block1.data
assert block0.hashed == block1.hashed
assert block0.max_nonce == block1.max_nonce
assert block0.timestamp == block1.timestamp
assert block0.nonce == block1.nonce
assert block0.hash == block1.hash
