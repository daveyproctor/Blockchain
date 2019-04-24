# Blockchain Implementation

Davey Proctor

## Setup

* Dependencies

    * Python3, no additional libraries needed

## Unit tests

* To test each class in the blockchain datastructure, run

    $ python3 test_[Block | Blockchain | DistributedBlockchain].py

## Simulations

* To see the simulation from the assignment in which four nodes interact in prescribed ways, start this code in each of four terminals at the same time (tmux synchronize-panes; really the simulation works even with some lag in starting, it's just less legible):

    $ python3 integration_test_gen_hon_dis_join.py [generator | honest | dishonest | joiner]

    * Note: the joiner is technically in the network all the time for simplicty; to simulate them joining from scratch; we have them set their chain to the empty set before requesting a new chain from everyone. This decision was made because it is easier to not have to connect more client sockets after some initial period, although my implementation with an ever-listening server makes this possible

* I also present a fuller three-node mining interaction. Start at the same time, and see these nodes mine an arbitrary number of blocks.

    $ python3 minerNode.py [generator | honest | joiner]

    * Note: The dishonest node can also be run, but its behavior is unintuitive as it intentionally rejects some inputs (it is dishonest after all)

## Discussion

* At the end of the first simulation, the system ends in a "forked" chain state, in which the graph of the superset of nodes' chains is a tree.

* One mustn't dispair at the possibility of a fork. For one, a longest valid chain exists, and so new nodes coming in such as the joiner will treat a single perceived blockchain history. Furthermore, a fork's longer chain will be maintained by a plurality of the nodes, meaning it's hard for even cooperating hackers to overtake the chain. The possibility of forks/failure of synchronization are an artifact of any distributed peer-to-peer networks; a blockchain aligns incentives to promote consistency. Close-to-perfect synchrony is all we can ask for. If we can't have it, we realized we never wanted it.


