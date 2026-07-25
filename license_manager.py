import sys
from license import generate_license

def main():
    if len(sys.argv) < 3:
        print("Usage: python license_manager.py <key> <days>")
        print("Example: python license_manager.py USER123 30")
        return
    key = sys.argv[1]
    try:
        days = int(sys.argv[2])
    except ValueError:
        print("❌ Days must be a number!")
        return
    generate_license(key, days)
    print(f"📋 License created for Key: {key} | Days: {days}")

if __name__ == "__main__":
    main()