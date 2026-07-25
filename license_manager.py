import sys
from license import generate_license
import os

def main():
    print("=== ZAW GYI License Generator ===")
    print("Enter user name and days for each user")
    print("Type 'q' to quit")
    print("-" * 30)
    
    while True:
        key = input("Enter user name: ").strip()
        if key.lower() == 'q':
            break
        if not key:
            print("User name cannot be empty!")
            continue
            
        try:
            days = int(input("Enter days: ").strip())
            if days <= 0:
                print("Days must be positive!")
                continue
            generate_license(key, days)
            print(f"License created for {key} | {days} days")
            if os.path.exists("license.json"):
                os.rename("license.json", f"license_{key}_{days}days.json")
                print(f"Saved as: license_{key}_{days}days.json")
        except ValueError:
            print("Please enter a valid number!")

if __name__ == "__main__":
    main()