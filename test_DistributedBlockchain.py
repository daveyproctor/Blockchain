# Unit tests for DistributedBlockchain class of blockchain.py
import blockchain
difficulty=16

distrBChain = blockchain.DistributedBlockchain(difficulty, "generator")
distrBChain._genesis()
distrBChain._generate()
distrBChain._generate()
assert len(distrBChain.chain) == 3
assert distrBChain.validate_chain()

# Serialize tests
distrBChain2 = blockchain.DistributedBlockchain(difficulty, "generator")
distrBChain2.deserialize_chain(distrBChain.serialize_chain())
assert distrBChain2.validate_chain()
assert str(distrBChain) == str(distrBChain2)
