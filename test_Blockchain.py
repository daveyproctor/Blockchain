# Unit tests for Blockchain class of blockchain.py
import blockchain
difficulty=16

block0 = blockchain.Block(0, '0', 'Genesis Block')
block0.search_hash(difficulty)
block1 = blockchain.Block(1, block0.hash, 'data1')
block1.search_hash(difficulty)
block2 = blockchain.Block(2, block1.hash, 'data2')
block2.search_hash(difficulty)


bchain = blockchain.Blockchain(difficulty)
assert bchain.validate(block2, block1)
assert bchain.validate(block1, block0)
assert bchain.validate(block0, "No_parent")
assert bchain.validate(block2, block0) == False

assert bchain.validate_chain()
assert bchain.add_block(block0)
assert bchain.validate_chain()
assert bchain.add_block(block1)
assert bchain.validate_chain()
assert bchain.add_block(block2)
assert bchain.validate_chain()





