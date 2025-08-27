from web3 import Web3
import json
from solcx import compile_source, install_solc

# Install Solidity compiler
install_solc('0.8.0')

# Read the smart contract
with open('FileIntegrity.sol', 'r') as file:
    contract_source_code = file.read()

# Compile the contract
compiled_sol = compile_source(contract_source_code)
contract_interface = compiled_sol['<stdin>:FileIntegrityMonitor']

# Configuration
INFURA_URL = 'https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID'  # Replace with your Infura URL
PRIVATE_KEY = 'YOUR_PRIVATE_KEY'  # Replace with your private key
ACCOUNT_ADDRESS = 'YOUR_ACCOUNT_ADDRESS'  # Replace with your account address

# Connect to Ethereum node
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Check connection
if not w3.is_connected():
    print("Failed to connect to Ethereum node")
    exit()

print("Connected to Ethereum node")
print(f"Account balance: {w3.eth.get_balance(ACCOUNT_ADDRESS)} Wei")

# Deploy contract
def deploy_contract():
    try:
        # Get contract
        contract = w3.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bin']
        )
        
        # Get account
        account = w3.eth.account.from_key(PRIVATE_KEY)
        
        # Build constructor transaction
        constructor_txn = contract.constructor().build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(constructor_txn, PRIVATE_KEY)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"Contract deployment transaction hash: {tx_hash.hex()}")
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Contract deployed at address: {tx_receipt.contractAddress}")
        
        # Save contract ABI and address
        contract_info = {
            'address': tx_receipt.contractAddress,
            'abi': contract_interface['abi']
        }
        
        with open('contract_info.json', 'w') as f:
            json.dump(contract_info, f, indent=2)
        
        with open('contract_abi.json', 'w') as f:
            json.dump(contract_interface['abi'], f, indent=2)
        
        print("Contract ABI and address saved to files")
        print("Deployment successful!")
        
        return tx_receipt.contractAddress
        
    except Exception as e:
        print(f"Deployment failed: {e}")
        return None

if __name__ == "__main__":
    deployed_address = deploy_contract()
    if deployed_address:
        print(f"\nUpdate your Flask app configuration with:")
        print(f"CONTRACT_ADDRESS = '{deployed_address}'")
        print(f"Make sure to also update your Infura URL and private key in the Flask app.")