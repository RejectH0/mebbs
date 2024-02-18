
# MeBBS - Meshtastic e Bulletin Board System

Welcome to MeBBS, your go-to Bulletin Board System (BBS) for the Meshtastic community! Designed to enhance connectivity and communication, MeBBS allows Meshtastic users to exchange personal messages through a robust and user-friendly platform. Whether you're deep in the wilderness or just exploring the capabilities of Meshtastic devices, MeBBS is here to keep you connected.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Before you dive into setting up MeBBS, ensure you have the following prerequisites installed on your system:

- Python 3.11 or later
- pip for Python 3
- MariaDB or MySQL server
- A Meshtastic device connected to your computer

### Installation

1. **Clone the repository**

   Start by cloning the repository to your local machine using git:

   ```bash
   git clone https://github.com/yourrepository/mebbs.git
   cd mebbs
   ```

2. **Install dependencies**

   Use pip to install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. **Database Configuration**

   - Make sure your MariaDB or MySQL server is running.
   - Create a `db_config.json` file in the root directory with the following structure, replacing the placeholder values with your actual database credentials:

     ```json
     {
       "hostname": "localhost",
       "port": 3306,
       "username": "your_username",
       "password": "your_password"
     }
     ```

4. **Run the Application**

   Execute the following command to start the Flask server:

   ```bash
   python app.py
   ```

   The server will start on `http://localhost:8080`. Open your browser and navigate to this address to access the MeBBS BBS.

### Usage

- **Meshtastic Device Information**: Access `/meshtastic/info` to get information about the connected Meshtastic device.
- **Send Commands**: Use the `/command` endpoint to simulate sending commands to the Meshtastic network.

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.

## Acknowledgments

- Meshtastic Project
- Flask Framework
- MariaDB
- All contributors and supporters of the MeBBS project

## About the Author:

Gregg (RejectH0) is a hobby programmer, familiar with programming in a multitude of contexts and languages, as well as versatile with the use of Large Language Models (LLMs) to assist with coding tasks. Gregg is also a hobby photographer and considers himself a student of linguistics, psychology, and computer science.
