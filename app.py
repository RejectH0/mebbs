# mebbs - v0.1 - 20240218-0050
# Gregg RejectH0 Projects
from flask import Flask, request, jsonify
import threading
import json
import mysql.connector
import subprocess
import re
import asyncio
from mysql.connector import Error
from meshtastic import StreamInterface

app = Flask(__name__)
meshtastic_info_cache = {}

# Placeholder for session management
sessions = {}

# Initialize Meshtastic interface
interface = StreamInterface()

def load_db_config():
    """Load database configuration from a local file."""
    with open('db_config.json', 'r') as file:
        return json.load(file)

def connect_to_mariadb(db_config):
    """Establish a connection to the MariaDB server."""
    try:
        connection = mysql.connector.connect(
            host=db_config['hostname'],
            port=db_config['port'],
            user=db_config['username'],
            password=db_config['password']
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        return None

def check_mebbs_databases(connection, shortName):
    """Check and initialize the 'mebbs_{shortName}' database."""
    try:
        cursor = connection.cursor()
        # Use the LIKE operator with the correct pattern for matching database names
        cursor.execute("SHOW DATABASES LIKE 'mebbs\\_%s'" % shortName)
        databases = cursor.fetchall()
        if len(databases) == 0:
            # If database does not exist, create it with underscores
            cursor.execute(f"CREATE DATABASE `mebbs_{shortName}`")
            print(f"Database 'mebbs_{shortName}' created.")
        else:
            print(f"Database 'mebbs_{shortName}' already exists.")
        cursor.close()
    except Error as e:
        print(f"Failed to check or create database: {e}")

async def get_meshtastic_info_async():
    """Executes 'meshtastic --info' command asynchronously and parses its output."""
    try:
        # Asynchronously execute the meshtastic command and capture its output
        process = await asyncio.create_subprocess_shell(
            'meshtastic --info',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        
        output = stdout.decode()
        
        if "Exception" in output or "Connected to radio" not in output:
            print("Error or no connection to radio detected.")
            return {}
        
        return parse_meshtastic_info_output(output)
    except Exception as e:
        print(f"Error executing meshtastic command asynchronously: {e}")
        return {}

def parse_meshtastic_info_output(output):
    """Parses the output from 'meshtastic --info' command."""
    info = {}
    
    # Check for successful connection
    if "Connected to radio" not in output:
        return {"error": "Failed to connect to radio"}
    
    # Example parsing logic for structured data extraction
    try:
        # Extract JSON-like structures
        nodes_info_match = re.search(r"Nodes in mesh: (\{.*\})", output, re.DOTALL)
        if nodes_info_match:
            nodes_info_str = nodes_info_match.group(1)
            info['nodes'] = json.loads(nodes_info_str)
        
        # Extract key-value pairs
        owner_match = re.search(r"Owner: (.*)", output)
        if owner_match:
            info['owner'] = owner_match.group(1)
        
        # Add more parsing as needed based on the output structure
        
    except Exception as e:
        print(f"Error parsing meshtastic info: {e}")
    
    return info

def create_table_nodes(connection):
    """Create the 'nodes' table with the structure based on 'Nodes in mesh'."""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nodeID VARCHAR(9) UNIQUE,
                num BIGINT,
                longName VARCHAR(64),
                shortName VARCHAR(4),
                macaddr VARCHAR(17),
                hwModel VARCHAR(64),
                role VARCHAR(64),
                latitudeI INT,
                longitudeI INT,
                altitude INT,
                time BIGINT,
                latitude DOUBLE,
                longitude DOUBLE,
                lastHeard BIGINT,
                batteryLevel TINYINT,
                voltage FLOAT,
                channelUtilization FLOAT,
                airUtilTx FLOAT,
                snr FLOAT,
                channel TINYINT
            )
        """)
        print("Table 'nodes' created or already exists.")
        cursor.close()
    except Error as e:
        print(f"Failed to create the 'nodes' table: {e}")

def create_table_preferences(connection):
    """Create the 'preferences' table with the structure based on 'Preferences' from meshtastic --info."""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nodeID VARCHAR(9) UNIQUE,
                device JSON,
                position JSON,
                power JSON,
                network JSON,
                display JSON,
                lora JSON,
                bluetooth JSON
            )
        """)
        print("Table 'preferences' created or already exists.")
        cursor.close()
    except Error as e:
        print(f"Failed to create the 'preferences' table: {e}")

def create_table_modulePreferences(connection):
    """Create the 'modulePreferences' table based on 'Module preferences' from meshtastic --info."""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modulePreferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nodeID VARCHAR(9) UNIQUE,
                mqtt JSON,
                serial JSON,
                externalNotification JSON,
                rangeTest JSON,
                telemetry JSON,
                cannedMessage JSON,
                audio JSON,
                remoteHardware JSON,
                neighborInfo JSON,
                ambientLighting JSON,
                detectionSensor JSON,
                paxcounter JSON
            )
        """)
        print("Table 'modulePreferences' created or already exists.")
        cursor.close()
    except Error as e:
        print(f"Failed to create the 'modulePreferences' table: {e}")

def create_table_channels(connection):
    """Create the 'channels' table based on 'Channels' from meshtastic --info."""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nodeID VARCHAR(9),
                channelType ENUM('PRIMARY', 'SECONDARY') NOT NULL,
                psk VARCHAR(255),
                name VARCHAR(255),
                uplinkEnabled BOOLEAN DEFAULT FALSE,
                downlinkEnabled BOOLEAN DEFAULT FALSE,
                UNIQUE KEY unique_channel (nodeID, name)
            )
        """)
        print("Table 'channels' created or already exists.")
        cursor.close()
    except Error as e:
        print(f"Failed to create the 'channels' table: {e}")

def update_table_nodes(connection, nodes_info):
    cursor = connection.cursor()
    for nodeID, nodeDetails in nodes_info.items():
        # Extracting node details
        num = nodeDetails['num']
        longName = nodeDetails['user']['longName']
        shortName = nodeDetails['user']['shortName']
        macaddr = nodeDetails['user']['macaddr']
        hwModel = nodeDetails['user']['hwModel']
        role = nodeDetails['user'].get('role', '')  # Adjusted for optional 'role'
        latitudeI = nodeDetails['position'].get('latitudeI', 0)
        longitudeI = nodeDetails['position'].get('longitudeI', 0)
        altitude = nodeDetails['position'].get('altitude', 0)
        time = nodeDetails['position'].get('time', 0)
        latitude = nodeDetails['position'].get('latitude', 0.0)
        longitude = nodeDetails['position'].get('longitude', 0.0)
        lastHeard = nodeDetails.get('lastHeard', 0)
        batteryLevel = nodeDetails['deviceMetrics'].get('batteryLevel', 0)
        voltage = nodeDetails['deviceMetrics'].get('voltage', 0.0)
        airUtilTx = nodeDetails['deviceMetrics'].get('airUtilTx', 0.0)  # Assuming airUtilTx might not be present
        channelUtilization = nodeDetails['deviceMetrics'].get('channelUtilization', 0.0)  # Assuming optional
        snr = nodeDetails.get('snr', 0.0)  # Assuming snr might not be present
        channel = nodeDetails.get('channel', 0)  # Assuming channel might be optional

        # Check if nodeID exists
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE nodeID = %s", (nodeID,))
        if cursor.fetchone()[0] == 0:
            # Insert new node
            cursor.execute("""
                INSERT INTO nodes (nodeID, num, longName, shortName, macaddr, hwModel, role, latitudeI, longitudeI, altitude, time, latitude, longitude, lastHeard, batteryLevel, voltage, airUtilTx, channelUtilization, snr, channel)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nodeID, num, longName, shortName, macaddr, hwModel, role, latitudeI, longitudeI, altitude, time, latitude, longitude, lastHeard, batteryLevel, voltage, airUtilTx, channelUtilization, snr, channel))
    connection.commit()
    cursor.close()

def handle_message(packet):
    """Process incoming messages from the Meshtastic network."""
    # Extract message and sender details
    # Placeholder for message handling logic

def listen_to_meshtastic():
    """Listen for messages from the Meshtastic network."""
    interface.addPacketListener(handle_message)

# Start listening to Meshtastic in a background thread
threading.Thread(target=listen_to_meshtastic, daemon=True).start()

@app.route('/meshtastic/info', methods=['GET'])
def meshtastic_info():
    """Endpoint to display Meshtastic device info."""
    info = get_meshtastic_info()
    return jsonify(info)

@app.route('/command', methods=['POST'])
def command():
    """Endpoint to simulate receiving commands from the Meshtastic network."""
    data = request.json
    # Placeholder for command processing logic
    return jsonify({"status": "received", "data": data})

if __name__ == '__main__':
    # Fetch and cache Meshtastic information at startup
    meshtastic_info_cache = get_meshtastic_info()
    
    # Your existing database connection logic can go here
    db_config = load_db_config()
    mariadb_connection = connect_to_mariadb(db_config)
    if mariadb_connection:
        print("Successfully connected to MariaDB")
        databases = check_mebbs_databases(mariadb_connection)
        print(f"Found 'mebbs-*' databases: {databases}")
        mariadb_connection.close()
    else:
        print("Failed to connect to MariaDB")
    
    app.run(debug=True, port=8080)
