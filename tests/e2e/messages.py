def client_created():
    return "Telegram client has been created with session."

def client_started():
    return "Telegram client has been started."

def client_disconnected():
    return "Telegram client has been disconnected."

def bot_response_timeout():
    return "The bot did not respond to the command within the specified time."

def video_not_returned():
    return "The bot did not return a video."

def video_test_success(filename):
    return f"Video test for {filename} completed successfully."

def video_not_found(filename):
    return f"Expected video {filename} does not exist."

def video_mismatch():
    return "The received video differs from the expected one."

def file_not_returned():
    return "The bot did not return a file."

def file_extension_mismatch(expected, received):
    return f"The bot returned a file with an incorrect extension. Expected {expected}, got {received}."

def file_not_found(filename):
    return f"Expected file {filename} does not exist."

def file_mismatch():
    return "The received file differs from the expected one."

def file_test_success(filename):
    return f"File test for {filename} completed successfully."

def missing_fragment(fragment, response):
    return f'Expected fragment "{fragment}" was not found in response "{response}".'

def hash_file_not_found():
    return "The file with expected hashes was not found."

def hash_not_found(filename):
    return f"Hash for the expected file {filename} was not found."
