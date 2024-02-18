# mebbs - v0.1 - 20240217-2337
# Gregg RejectH0 Projects
from flask import Flask, request, jsonify
import threading
import json
import mysql.connector
import subprocess
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

def get_meshtastic_info():
    """Executes 'meshtastic --info' command and parses its JSON output."""
    try:
        # Execute the meshtastic command and capture its JSON output
        result = subprocess.run(['meshtastic', '--info', '--json'], capture_output=True, text=True, check=True)
        # Parse the JSON output
        info = json.loads(result.stdout)

        # Extracting the required information
        myNodeNum = info['myNodeNum']
        firmwareVersion = info.get('firmwareVersion', '')
        role = info.get('role', '')
        hwModel = info.get('hwModel', '')

        # Find the node in 'Nodes in mesh' that matches 'myNodeNum'
        nodes_in_mesh = info.get('nodes', {})
        myNode = nodes_in_mesh.get(str(myNodeNum), {})
        user = myNode.get('user', {})
        longName = user.get('longName', '')
        shortName = user.get('shortName', '')
        batteryLevel = myNode.get('deviceMetrics', {}).get('batteryLevel', 0)
        voltage = myNode.get('deviceMetrics', {}).get('voltage', 0)

        # Collecting channels information
        channels = info.get('channels', [])
        channel_names = [channel.get('name', '') for channel in channels]

        # Return the collected information
        return {
            "myNodeNum": myNodeNum,
            "firmwareVersion": firmwareVersion,
            "role": role,
            "hwModel": hwModel,
            "longName": longName,
            "shortName": shortName,
            "batteryLevel": batteryLevel,
            "voltage": voltage,
            "channels": channel_names
        }
    except subprocess.CalledProcessError as e:
        print(f"Error executing meshtastic command: {e}")
        return {}

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
