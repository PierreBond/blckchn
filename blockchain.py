import hashlib
import json
from time import time
from uuid import uuid4
from textwrap import dedent
from urllib.parse import urlparse

from flask import Flask, jsonify, request

import requests



class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        self.nodes = set()

        # creation of genesis block
        self.new_block(previous_hash=1,  proof=100)

    def new_block(self, proof, previous_hash=None):
        # creates a new block and adds it to the chain pass

        # :param proof: <int> the proof given by the proof of work algorithm
        # :param previous_hash: (optional) <str> hash of the previous hash
        # :return: <dict> new block

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transaction': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),

        }

        #reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def register_node(self, address):
        # Add a new node to the lsit of nodes
        # :param address:<str> address of node. Eg 'http//192.168.0.5:50'
        # :return: none

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):

        # determine if a given blockchain is valid
        # :param chain: <list> A blockchain
        # :return: <bool> True if valid, False if not

        last_block = chain[0]
        current_index = 1

        while current_index <  len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")

            # check that the hash of the block is correct

            if block['previous_hash'] != self.hash(last_block):
                return  False

            # check that the proof of work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):

        # this is our Consensus Algo, it resolves conflicts by replacing our
        # chain with the longest one in the network.
        # :return: <bool> true if our chain is replaced , False if not

        neighbours = self.nodes
        new_chain = None

        # we're only looking for the chains longer than ours
        max_length = len(self.chain)

        # grab and verify the chain from all the nodes in out network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        # replace our chain if we discover a new , valid chain longer than ours
        if new_chain :
            self.chain = new_chain
            return True

        return False

    def new_transaction(self, sender, recipient, amount):
        #adds a new transaction to the list of transactions pass
        #
        # Create a new transaction to go into the next mined block
        # :param sender: <str> Address of the sender
        # :param receiver: <str> Address of the receiver
        # :param amount: <int> Amount
        # :return: <int> The index of the blockthhat will hold this transaction

        self.current_transactions.append(
            {
                'sender' : sender,
                'recipient' : recipient,
                'amount' : amount,
            }
        )

        return self.last_block['index'] + 1

        # this method adds a trans  to the list returns the index to the block which the
        # trans will be added to the next one to be mined.

    @property

    def last_block(self):
        #returns the last block in the chain pass
        return self.chain[-1]


    @staticmethod
    def hash(block):
        #Hashes a block pass

        # create a SHA-256 hash of a block
        # :param block: <dict> Block
        # :return: <str>

        #we must make sure that the dictionary is ordered , or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):

        # simple Proof of Work ALgorithm:
        # -find a number p' such that hash(pp') contains leading 4 zeros, where p is the previous p'
        # -p is the previous proof , and p' is the new proof
        # :param last_proof: <int>
        # :return: <int>

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):

        # validate the proof: Does hash (last_proof, proof) ocontain 4 leading zeros?
        # :param last_proof: <int> previous proof
        # :param proof: <int> current proof
        # :return: <bool> true if correct , False if not

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    #BLOCKCHAIN AS AN API

#node initiation
app = Flask(__name__)

#generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

#instantiate blockchain

blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    return "We'll mine a new Block"
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    return "We'll add a new transaction"

@app.route('/chain', methods =['GET'])
def full_chain():
    response = {
        'chain':blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response),200

if __name__ == '__main__' :
    app.run(host='0.0.0.0', port=5000)


#function for adding transactions

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    #check that the required feilds are in the POST'ed data
    required = [ 'sender', 'recipient', 'amount']

    if not all(k in values for k in required):
        return 'Missing values', 400

    #create a new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block{index}'}
    return jsonify(response), 201

#MINING ENDPOINT

@app.route('/mine', methods=['GET'])
def mine():
    # we want PoW algorithm to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # we must receive a reward for finding the proof
    #the sender is "0" to signify that this node has mined a new coin

    blockchain.new_transaction(
        sender="0",
        recipient= node_identifier,
        amount=1,
    )

    #forge the new block by addind it to the chain

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message' : "New Block Forged",
        'index' : block['index'],
        'transactions' : block['transactions'],
        'proof' : block['proof'],
        'previous_hash' : block['previous_hash']
    }
    return jsonify(response), 200

#REGISTERING AND RESOLVING NODES
@app.route('/nodes/register', methods =['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error : Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message' : 'New modes have been added',
        'total_nodes' : list(blockchain.nodes),
    }
    return jsonify(response), 201
@app.route('/nodes/resolve', methods =['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response ={
            'message' : 'Our chain was replaced',
            'new_chain' : blockchain.chain
        }
    else:
        response = {
            'message' : 'Our chain is authoritative',
            'chain' : blockchain.chain
        }
    return jsonify(response), 200
