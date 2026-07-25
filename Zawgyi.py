# License check
from license import verify_license

def check_license_before_start():
    valid, msg = verify_license()
    if not valid:
        print(f"\n{msg}")
        print("\nPlease contact @Zawgyi1296 to get a valid license.")
        return False
    print(f"\n{msg}")
    return True