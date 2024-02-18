from flask import Flask, request, jsonify
import threading
import json
import mysql.connector
from mysql.connector import Error
from meshtastic import StreamInterface

app = Flask(__name__)

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

def check_mebbs_databases(connection):
    """Check for the existence of databases matching the pattern 'mebbs-*'."""
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall() if db[0].startswith('mebbs-')]
        return databases
    except Error as e:
        print(f"Failed to retrieve databases: {e}")
        return []

def handle_message(packet):
    """Process incoming messages from the Meshtastic network."""
    # Extract message and sender details
    # Placeholder for message handling logic

def listen_to_meshtastic():
    """Listen for messages from the Meshtastic network."""
    interface.addPacketListener(handle_message)

# Start listening to Meshtastic in a background thread
threading.Thread(target=listen_to_meshtastic, daemon=True).start()

@app.route('/command', methods=['POST'])
def command():
    """Endpoint to simulate receiving commands from the Meshtastic network."""
    data = request.json
    # Placeholder for command processing logic
    return jsonify({"status": "received", "data": data})

if __name__ == '__main__':
    db_config = load_db_config()
    mariadb_connection = connect_to_mariadb(db_config)
    if mariadb_connection:
        print("Successfully connected to MariaDB")
        databases = check_mebbs_databases(mariadb_connection)
        print(f"Found 'mebbs-*' databases: {databases}")
        mariadb_connection.close()
    else:
        print("Failed to connect to MariaDB")
    app.run(debug=True)
