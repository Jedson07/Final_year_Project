from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import os
import json
import time
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from web3 import Web3
from datetime import datetime
import sqlite3

app = Flask(__name__)
CORS(app)

# Configuration
BLOCKCHAIN_CONFIG = {
    'provider_url': 'https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID',
    'contract_address': '0xYOUR_CONTRACT_ADDRESS',
    'private_key': 'YOUR_PRIVATE_KEY',
    'abi': []  # Contract ABI will be loaded from file
}

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'username': 'your_email@gmail.com',
    'password': 'your_app_password'
}

class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self, file_monitor):
        self.file_monitor = file_monitor
        
    def on_modified(self, event):
        if not event.is_directory:
            self.file_monitor.handle_file_change(event.src_path, 'modified')
    
    def on_created(self, event):
        if not event.is_directory:
            self.file_monitor.handle_file_change(event.src_path, 'created')
    
    def on_deleted(self, event):
        if not event.is_directory:
            self.file_monitor.handle_file_change(event.src_path, 'deleted')

class FileIntegrityMonitor:
    def __init__(self):
        self.monitored_files = {}
        self.observers = {}
        self.w3 = None
        self.contract = None
        self.init_blockchain()
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for local storage"""
        conn = sqlite3.connect('file_monitor.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitored_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                file_hash TEXT,
                last_modified TIMESTAMP,
                user_email TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                alert_type TEXT,
                timestamp TIMESTAMP,
                details TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def init_blockchain(self):
        """Initialize blockchain connection"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_CONFIG['provider_url']))
            # Load contract ABI from file
            with open('contract_abi.json', 'r') as f:
                abi = json.load(f)
                self.contract = self.w3.eth.contract(
                    address=BLOCKCHAIN_CONFIG['contract_address'],
                    abi=abi
                )
        except Exception as e:
            print(f"Blockchain initialization failed: {e}")
    
    def calculate_file_hash(self, file_path):
        """Calculate SHA-256 hash of a file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def register_file_on_blockchain(self, file_path, file_hash):
        """Register file hash on blockchain"""
        try:
            if not self.contract:
                return False
                
            account = self.w3.eth.account.from_key(BLOCKCHAIN_CONFIG['private_key'])
            
            # Build transaction
            txn = self.contract.functions.registerFile(file_path, file_hash).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(txn, BLOCKCHAIN_CONFIG['private_key'])
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt.status == 1
            
        except Exception as e:
            print(f"Blockchain registration failed: {e}")
            return False
    
    def verify_file_integrity(self, file_path, current_hash):
        """Verify file integrity on blockchain"""
        try:
            if not self.contract:
                return True  # Skip verification if blockchain unavailable
                
            account = self.w3.eth.account.from_key(BLOCKCHAIN_CONFIG['private_key'])
            
            # Call verification function
            result = self.contract.functions.verifyFileIntegrity(
                file_path, current_hash
            ).call({'from': account.address})
            
            return result
            
        except Exception as e:
            print(f"Blockchain verification failed: {e}")
            return True
    
    def send_alert_email(self, recipient_email, file_path, alert_type):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['username']
            msg['To'] = recipient_email
            msg['Subject'] = f"File Integrity Alert - {alert_type}"
            
            body = f"""
            SECURITY ALERT: File Integrity Monitoring System
            
            Alert Type: {alert_type}
            File Path: {file_path}
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            A file under monitoring has been modified or accessed without authorization.
            Please check your system immediately.
            
            This is an automated alert from your File Integrity Monitoring System.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Email alert failed: {e}")
            return False
    
    def add_file_to_monitor(self, file_path, user_email):
        """Add a file to monitoring system"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "message": "File does not exist"}
            
            # Calculate initial hash
            file_hash = self.calculate_file_hash(file_path)
            if not file_hash:
                return {"success": False, "message": "Failed to calculate file hash"}
            
            # Store in database
            conn = sqlite3.connect('file_monitor.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO monitored_files 
                (file_path, file_hash, last_modified, user_email) 
                VALUES (?, ?, ?, ?)
            ''', (file_path, file_hash, datetime.now(), user_email))
            conn.commit()
            conn.close()
            
            # Register on blockchain
            blockchain_success = self.register_file_on_blockchain(file_path, file_hash)
            
            # Start monitoring directory
            directory = os.path.dirname(file_path)
            if directory not in self.observers:
                event_handler = FileMonitorHandler(self)
                observer = Observer()
                observer.schedule(event_handler, directory, recursive=False)
                observer.start()
                self.observers[directory] = observer
            
            self.monitored_files[file_path] = {
                'hash': file_hash,
                'email': user_email,
                'blockchain_registered': blockchain_success
            }
            
            return {
                "success": True, 
                "message": "File added to monitoring",
                "blockchain_registered": blockchain_success
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def handle_file_change(self, file_path, change_type):
        """Handle file change events"""
        if file_path not in self.monitored_files:
            return
        
        try:
            current_hash = self.calculate_file_hash(file_path)
            if not current_hash:
                return
            
            stored_info = self.monitored_files[file_path]
            
            if current_hash != stored_info['hash']:
                # File has been modified - potential intrusion
                print(f"INTRUSION DETECTED: {file_path}")
                
                # Verify on blockchain
                integrity_verified = self.verify_file_integrity(file_path, current_hash)
                
                # Log alert
                conn = sqlite3.connect('file_monitor.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts (file_path, alert_type, timestamp, details)
                    VALUES (?, ?, ?, ?)
                ''', (file_path, 'File Modified', datetime.now(), 
                      f"Hash changed from {stored_info['hash']} to {current_hash}"))
                conn.commit()
                conn.close()
                
                # Send email alert
                self.send_alert_email(
                    stored_info['email'], 
                    file_path, 
                    "File Modification Detected"
                )
                
                # Update stored hash
                stored_info['hash'] = current_hash
                
        except Exception as e:
            print(f"Error handling file change: {e}")

# Global monitor instance
file_monitor = FileIntegrityMonitor()

# Flask Routes
@app.route('/api/add_file', methods=['POST'])
def add_file():
    data = request.json
    file_path = data.get('file_path')
    user_email = data.get('user_email')
    
    if not file_path or not user_email:
        return jsonify({"success": False, "message": "Missing file path or email"}), 400
    
    result = file_monitor.add_file_to_monitor(file_path, user_email)
    return jsonify(result)

@app.route('/api/monitored_files', methods=['GET'])
def get_monitored_files():
    try:
        conn = sqlite3.connect('file_monitor.db')
        cursor = conn.cursor()
        cursor.execute('SELECT file_path, file_hash, last_modified, user_email FROM monitored_files WHERE is_active = 1')
        files = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "files": [
                {
                    "file_path": f[0],
                    "file_hash": f[1],
                    "last_modified": f[2],
                    "user_email": f[3]
                } for f in files
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        conn = sqlite3.connect('file_monitor.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 50')
        alerts = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "alerts": [
                {
                    "id": a[0],
                    "file_path": a[1],
                    "alert_type": a[2],
                    "timestamp": a[3],
                    "details": a[4]
                } for a in alerts
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/remove_file', methods=['POST'])
def remove_file():
    data = request.json
    file_path = data.get('file_path')
    
    try:
        conn = sqlite3.connect('file_monitor.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE monitored_files SET is_active = 0 WHERE file_path = ?', (file_path,))
        conn.commit()
        conn.close()
        
        if file_path in file_monitor.monitored_files:
            del file_monitor.monitored_files[file_path]
        
        return jsonify({"success": True, "message": "File removed from monitoring"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "success": True,
        "message": "File Integrity Monitoring System is running",
        "blockchain_connected": file_monitor.w3 is not None and file_monitor.w3.is_connected()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)