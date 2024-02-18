#!./bin/python3
# mebbs - v0.1 - 20240218-0320
# Gregg RejectH0 Projects
from flask import Flask, request, jsonify
import threading
import json
import mysql.connector
import subprocess
import re
import asyncio
import yaml
import meshtastic
import meshtastic.tcp_interface
from pubsub import pub
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
meshtastic_info_cache = {}

# Placeholder for session management
sessions = {}

# Initialize Meshtastic Serial interface
# interface = meshtastic.serial_interface.SerialInterface()

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

def check_mebbs_database(connection, shortName):
    """Check and initialize the 'mebbs_{shortName}' database, adjusting for dynamic shortName values."""
    try:
        cursor = connection.cursor()
        dbName = f"mebbs_{shortName}"
        # Directly check for the specific database name
        cursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (dbName,))
        if cursor.fetchone() is None:
            # If database does not exist, create it
            cursor.execute(f"CREATE DATABASE `{dbName}`")
            feedback = f"Database '{dbName}' created."
        else:
            feedback = f"Database '{dbName}' already exists."
        
        # Select the database for use
        connection.database = dbName
        feedback += f" Using database '{dbName}'."
        
        print(feedback)  # Print server feedback
        cursor.close()
    except Error as e:
        print(f"Failed to check or create and select database: {e}")

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

    try:
        # Extract "Nodes in mesh" as JSON
        nodes_info_match = re.search(r"Nodes in mesh: (\{.*\})", output, re.DOTALL)
        if nodes_info_match:
            nodes_info_str = nodes_info_match.group(1)
            info['nodes'] = json.loads(nodes_info_str)

        # Extract simple key-value pairs (example: Owner)
        owner_match = re.search(r"Owner: (.*)", output)
        if owner_match:
            info['owner'] = owner_match.group(1)

        # Extract "My info" as JSON
        my_info_match = re.search(r"My info: (\{.*\})", output, re.DOTALL)
        if my_info_match:
            my_info_str = my_info_match.group(1)
            info['myInfo'] = json.loads(my_info_str)

        # Extract "Metadata" as JSON
        metadata_match = re.search(r"Metadata: (\{.*\})", output, re.DOTALL)
        if metadata_match:
            metadata_str = metadata_match.group(1)
            info['metadata'] = json.loads(metadata_str)

        # Preferences and Module preferences can be extracted similarly to "My info" and "Metadata"
        # Channels extraction would require parsing the listed channels, potentially with a loop or additional regex

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

def update_table_channels(connection, channels_info):
    """Update the 'channels' table with channels from Meshtastic info."""
    try:
        cursor = connection.cursor()
        for channel_type, details in channels_info.items():
            # Assuming 'channels_info' is a dict with channel types as keys and details as values
            psk = details.get('psk', '')
            name = details.get('name', '')
            uplinkEnabled = details.get('uplinkEnabled', False)
            downlinkEnabled = details.get('downlinkEnabled', False)

            # Check if channel exists
            cursor.execute("SELECT COUNT(*) FROM channels WHERE name = %s", (name,))
            if cursor.fetchone()[0] == 0:
                # Insert new channel
                cursor.execute("""
                    INSERT INTO channels (channelType, psk, name, uplinkEnabled, downlinkEnabled)
                    VALUES (%s, %s, %s, %s, %s)
                """, (channel_type.upper(), psk, name, uplinkEnabled, downlinkEnabled))
            else:
                # Update existing channel
                cursor.execute("""
                    UPDATE channels
                    SET psk = %s, uplinkEnabled = %s, downlinkEnabled = %s
                    WHERE name = %s
                """, (psk, uplinkEnabled, downlinkEnabled, name))
        connection.commit()
    except Error as e:
        print(f"Failed to update the 'channels' table: {e}")
    finally:
        cursor.close()

def handle_message(packet):
    """Process incoming messages from the Meshtastic network."""
    # Extract message and sender details from the packet
    message = packet.get('decoded').get('text')
    sender = packet.get('from').get('callsign')

    # Determine message type and take appropriate action
    if message:
        # Process text message
        print(f"Received message from {sender}: {message}")

def listen_to_meshtastic():
    """Listen for messages from the Meshtastic network."""
    interface.on_receive(handle_message)

async def fetch_meshtastic_config_async():
    """Fetches Meshtastic configuration asynchronously and parses its YAML output."""
    try:
        process = await asyncio.create_subprocess_shell(
            'meshtastic --export-config',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()

        output = stdout.decode()

        if "Exception" in output:
            print("Error fetching Meshtastic config.")
            return {}

        # Parse YAML output
        config = yaml.safe_load(output)
        return config
    except Exception as e:
        print(f"Error fetching Meshtastic config asynchronously: {e}")
        return {}

# Start listening to Meshtastic in a background thread
#threading.Thread(target=listen_to_meshtastic, daemon=True).start()

def onReceive(packet, interface):
    print(f"Received: {packet}")

async def init_mebbs():
    print("Loading database configuration...")
    db_config = load_db_config()
    
    print("Fetching Meshtastic configuration asynchronously...")
    meshtastic_config = await fetch_meshtastic_config_async()
    
    if not meshtastic_config:
        print("Failed to fetch Meshtastic config. Exiting.")
        return
    
    owner = meshtastic_config.get('owner', 'n0own3r').strip("'")
    owner_short = meshtastic_config.get('owner_short', '0000').strip("'")
    print(f"Owner name: {owner}")
    print(f"Owner short name: {owner_short}")
    # Get current date and time
    current_time = datetime.now().strftime("%Y/%m/%d - %H:%M:%S")

    # Format the message
    message = f"{owner} ({owner_short}): Now online {current_time}"

    # Send the message
    interface.sendText(message)

    print("Connecting to MariaDB...")
    mariadb_connection = connect_to_mariadb(db_config)
    
    if mariadb_connection:
        print("Successfully connected to MariaDB. Checking/creating database...")
        check_mebbs_database(mariadb_connection, owner_short)
        
        print("Creating 'nodes' table...")
        create_table_nodes(mariadb_connection)
        
        print("Creating 'preferences' table...")
        create_table_preferences(mariadb_connection)
        
        print("Creating 'modulePreferences' table...")
        create_table_modulePreferences(mariadb_connection)
        
        print("Creating 'channels' table...")
        create_table_channels(mariadb_connection)

        # Update nodes table
        print("Updating 'nodes' table with current Meshtastic nodes...")
        update_table_nodes(mariadb_connection, meshtastic_config['nodes'])

        # Update channels table
        print("Updating 'channels' table with current Meshtastic channels...")
        update_table_channels(mariadb_connection, meshtastic_config['channels'])

        print("Closing MariaDB connection.")
        mariadb_connection.close()
    else:
        print("Error in init_mebbs(): Failed to connect to MariaDB.")

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

def main():
    print("Initializing MEBBS application...")
    asyncio.run(init_mebbs())
    print("MEBBS application initialized successfully.")

if __name__ == '__main__':
    print("Starting Flask app...")
    main()
    app.run(debug=True, port=8080)
