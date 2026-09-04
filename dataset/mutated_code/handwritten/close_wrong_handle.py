def copy_streams(src_path: str, dst_path: str):
    f1 = open(src_path, "r")
    f2 = open(dst_path, "w")
    try:
        f2.write(f1.read())
    finally:
        f2.close()
        f2.close()
