import tempfile

def write_temp_data(payload: bytes):
    tf = tempfile.NamedTemporaryFile(delete=False)
    try:
        tf.write(payload)
        tf.flush()
    finally:
        pass
