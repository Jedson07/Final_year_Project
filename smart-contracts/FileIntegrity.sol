// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FileIntegrityMonitor {
    struct FileRecord {
        string filePath;
        string fileHash;
        uint256 timestamp;
        address owner;
        bool isActive;
    }
    
    mapping(string => FileRecord) public fileRecords;
    mapping(address => string[]) public userFiles;
    
    event FileRegistered(string indexed filePath, string fileHash, address indexed owner, uint256 timestamp);
    event FileModified(string indexed filePath, string oldHash, string newHash, uint256 timestamp);
    event IntrusionDetected(string indexed filePath, address indexed owner, uint256 timestamp);
    
    modifier onlyFileOwner(string memory filePath) {
        require(fileRecords[filePath].owner == msg.sender, "Not authorized to access this file");
        _;
    }
    
    function registerFile(string memory filePath, string memory fileHash) public {
        require(bytes(filePath).length > 0, "File path cannot be empty");
        require(bytes(fileHash).length > 0, "File hash cannot be empty");
        
        if (fileRecords[filePath].owner == address(0)) {
            // New file registration
            userFiles[msg.sender].push(filePath);
        }
        
        fileRecords[filePath] = FileRecord({
            filePath: filePath,
            fileHash: fileHash,
            timestamp: block.timestamp,
            owner: msg.sender,
            isActive: true
        });
        
        emit FileRegistered(filePath, fileHash, msg.sender, block.timestamp);
    }
    
    function verifyFileIntegrity(string memory filePath, string memory currentHash) 
        public 
        onlyFileOwner(filePath) 
        returns (bool) 
    {
        FileRecord storage record = fileRecords[filePath];
        require(record.isActive, "File is not being monitored");
        
        if (keccak256(abi.encodePacked(record.fileHash)) != keccak256(abi.encodePacked(currentHash))) {
            emit IntrusionDetected(filePath, msg.sender, block.timestamp);
            emit FileModified(filePath, record.fileHash, currentHash, block.timestamp);
            
            // Update the hash after detecting tampering
            record.fileHash = currentHash;
            record.timestamp = block.timestamp;
            
            return false; // File has been tampered with
        }
        
        return true; // File integrity maintained
    }
    
    function getFileRecord(string memory filePath) 
        public 
        view 
        onlyFileOwner(filePath) 
        returns (FileRecord memory) 
    {
        return fileRecords[filePath];
    }
    
    function getUserFiles(address user) public view returns (string[] memory) {
        return userFiles[user];
    }
    
    function deactivateFileMonitoring(string memory filePath) 
        public 
        onlyFileOwner(filePath) 
    {
        fileRecords[filePath].isActive = false;
    }
    
    function getFileCount(address user) public view returns (uint256) {
        return userFiles[user].length;
    }
}