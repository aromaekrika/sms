import serial
import time

# List of possible serial ports to try
POSSIBLE_PORTS = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyAMA0', '/dev/ttyS0']

# Initialize the serial connection for SMS
serial_port = None
for port in POSSIBLE_PORTS:
    try:
        serial_port = serial.Serial(port, 9600, timeout=1)  # Adjust the baud rate as needed
        print(f"Serial port initialized successfully on {port}.")
        break  # Stop trying ports once a valid one is found
    except serial.SerialException as e:
        print(f"Error initializing serial port on {port}: {e}")
        serial_port = None  # Reset to None if the port is unavailable

if serial_port is None:
    print("No valid serial port found. SMS functionality will be disabled.")

def get_phone_number():
    """
    Query the GSM modem for its phone number using the AT+CNUM command.
    Returns the phone number if detected, otherwise returns None.
    """
    if serial_port is None:
        return None

    try:
        # Send the AT+CNUM command to query the phone number
        serial_port.write(b'AT+CNUM\r')
        time.sleep(1)  # Wait for the response

        # Read the response
        response = serial_port.read_all().decode('utf-8').strip()

        # Parse the response to extract the phone number
        if '+CNUM:' in response:
            lines = response.splitlines()
            for line in lines:
                if '+CNUM:' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        phone_number = parts[1].strip('"')
                        return phone_number
        return None
    except Exception as e:
        print(f"Error querying phone number: {e}")
        return None