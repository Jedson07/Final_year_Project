import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:file_picker/file_picker.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'File Integrity Monitor',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  @override
  _HomePageState createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final String baseUrl = 'http://localhost:5000/api';
  final TextEditingController emailController = TextEditingController();
  List<Map<String, dynamic>> monitoredFiles = [];
  List<Map<String, dynamic>> alerts = [];
  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    loadMonitoredFiles();
    loadAlerts();
  }

  Future<void> loadMonitoredFiles() async {
    setState(() {
      isLoading = true;
    });

    try {
      final response = await http.get(Uri.parse('$baseUrl/monitored_files'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success']) {
          setState(() {
            monitoredFiles = List<Map<String, dynamic>>.from(data['files']);
          });
        }
      }
    } catch (e) {
      _showSnackBar('Error loading files: $e');
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Future<void> loadAlerts() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/alerts'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success']) {
          setState(() {
            alerts = List<Map<String, dynamic>>.from(data['alerts']);
          });
        }
      }
    } catch (e) {
      print('Error loading alerts: $e');
    }
  }

  Future<void> addFileToMonitor() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles();
    
    if (result != null && result.files.single.path != null) {
      String filePath = result.files.single.path!;
      String email = emailController.text.trim();
      
      if (email.isEmpty) {
        _showSnackBar('Please enter your email address');
        return;
      }

      setState(() {
        isLoading = true;
      });

      try {
        final response = await http.post(
          Uri.parse('$baseUrl/add_file'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'file_path': filePath,
            'user_email': email,
          }),
        );

        final data = json.decode(response.body);
        
        if (data['success']) {
          _showSnackBar('File added to monitoring successfully!');
          loadMonitoredFiles();
        } else {
          _showSnackBar('Error: ${data['message']}');
        }
      } catch (e) {
        _showSnackBar('Error adding file: $e');
      } finally {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  Future<void> removeFileFromMonitor(String filePath) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/remove_file'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'file_path': filePath}),
      );

      final data = json.decode(response.body);
      
      if (data['success']) {
        _showSnackBar('File removed from monitoring');
        loadMonitoredFiles();
      } else {
        _showSnackBar('Error: ${data['message']}');
      }
    } catch (e) {
      _showSnackBar('Error removing file: $e');
    }
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('File Integrity Monitor'),
        backgroundColor: Colors.blue[800],
        elevation: 0,
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.blue[800]!, Colors.blue[50]!],
          ),
        ),
        child: Column(
          children: [
            // Header Section
            Container(
              padding: EdgeInsets.all(20),
              child: Card(
                elevation: 8,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(15),
                ),
                child: Padding(
                  padding: EdgeInsets.all(20),
                  child: Column(
                    children: [
                      Icon(
                        Icons.security,
                        size: 50,
                        color: Colors.blue[800],
                      ),
                      SizedBox(height: 10),
                      Text(
                        'Blockchain-Based File Integrity Monitor',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Colors.blue[800],
                        ),
                        textAlign: TextAlign.center,
                      ),
                      SizedBox(height: 20),
                      TextField(
                        controller: emailController,
                        decoration: InputDecoration(
                          labelText: 'Email for Alerts',
                          prefixIcon: Icon(Icons.email),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                        keyboardType: TextInputType.emailAddress,
                      ),
                      SizedBox(height: 20),
                      ElevatedButton.icon(
                        onPressed: isLoading ? null : addFileToMonitor,
                        icon: Icon(Icons.add_circle),
                        label: Text('Add File to Monitor'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue[800],
                          padding: EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            
            // Tabs Section
            Expanded(
              child: DefaultTabController(
                length: 2,
                child: Column(
                  children: [
                    TabBar(
                      labelColor: Colors.blue[800],
                      unselectedLabelColor: Colors.grey,
                      indicatorColor: Colors.blue[800],
                      tabs: [
                        Tab(
                          icon: Icon(Icons.folder_special),
                          text: 'Monitored Files',
                        ),
                        Tab(
                          icon: Icon(Icons.warning),
                          text: 'Alerts',
                        ),
                      ],
                    ),
                    Expanded(
                      child: TabBarView(
                        children: [
                          // Monitored Files Tab
                          Container(
                            padding: EdgeInsets.all(15),
                            child: isLoading
                                ? Center(child: CircularProgressIndicator())
                                : monitoredFiles.isEmpty
                                    ? Center(
                                        child: Column(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            Icon(
                                              Icons.folder_open,
                                              size: 80,
                                              color: Colors.grey,
                                            ),
                                            Text(
                                              'No files being monitored',
                                              style: TextStyle(
                                                fontSize: 18,
                                                color: Colors.grey,
                                              ),
                                            ),
                                          ],
                                        ),
                                      )
                                    : ListView.builder(
                                        itemCount: monitoredFiles.length,
                                        itemBuilder: (context, index) {
                                          final file = monitoredFiles[index];
                                          return Card(
                                            margin: EdgeInsets.symmetric(vertical: 5),
                                            elevation: 3,
                                            shape: RoundedRectangleBorder(
                                              borderRadius: BorderRadius.circular(10),
                                            ),
                                            child: ListTile(
                                              leading: Icon(
                                                Icons.insert_drive_file,
                                                color: Colors.blue[800],
                                                size: 30,
                                              ),
                                              title: Text(
                                                file['file_path'].split('/').last,
                                                style: TextStyle(fontWeight: FontWeight.bold),
                                              ),
                                              subtitle: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  Text(
                                                    'Path: ${file['file_path']}',
                                                    style: TextStyle(fontSize: 12),
                                                  ),
                                                  Text(
                                                    'Hash: ${file['file_hash'].substring(0, 16)}...',
                                                    style: TextStyle(fontSize: 10, fontFamily: 'Courier'),
                                                  ),
                                                  Text(
                                                    'Modified: ${file['last_modified']}',
                                                    style: TextStyle(fontSize: 10),
                                                  ),
                                                ],
                                              ),
                                              trailing: IconButton(
                                                icon: Icon(Icons.delete, color: Colors.red),
                                                onPressed: () => removeFileFromMonitor(file['file_path']),
                                              ),
                                            ),
                                          );
                                        },
                                      ),
                          ),
                          
                          // Alerts Tab
                          Container(
                            padding: EdgeInsets.all(15),
                            child: alerts.isEmpty
                                ? Center(
                                    child: Column(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Icon(
                                          Icons.check_circle,
                                          size: 80,
                                          color: Colors.green,
                                        ),
                                        Text(
                                          'No alerts - All files secure',
                                          style: TextStyle(
                                            fontSize: 18,
                                            color: Colors.green,
                                          ),
                                        ),
                                      ],
                                    ),
                                  )
                                : ListView.builder(
                                    itemCount: alerts.length,
                                    itemBuilder: (context, index) {
                                      final alert = alerts[index];
                                      return Card(
                                        margin: EdgeInsets.symmetric(vertical: 5),
                                        elevation: 3,
                                        color: Colors.red[50],
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(10),
                                          side: BorderSide(color: Colors.red[200]!),
                                        ),
                                        child: ListTile(
                                          leading: Icon(
                                            Icons.warning,
                                            color: Colors.red,
                                            size: 30,
                                          ),
                                          title: Text(
                                            alert['alert_type'],
                                            style: TextStyle(
                                              fontWeight: FontWeight.bold,
                                              color: Colors.red[800],
                                            ),
                                          ),
                                          subtitle: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                'File: ${alert['file_path']}',
                                                style: TextStyle(fontSize: 12),
                                              ),
                                              Text(
                                                'Time: ${alert['timestamp']}',
                                                style: TextStyle(fontSize: 10),
                                              ),
                                              if (alert['details'] != null)
                                                Text(
                                                  'Details: ${alert['details']}',
                                                  style: TextStyle(fontSize: 10),
                                                ),
                                            ],
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          loadMonitoredFiles();
          loadAlerts();
        },
        child: Icon(Icons.refresh),
        backgroundColor: Colors.blue[800],
        tooltip: 'Refresh Data',
      ),
    );
  }
}