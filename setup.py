#!/usr/bin/env python3
"""
AI Quiz Assistant Setup Script
Configure Gemini API credentials
"""

import os
import json
import hashlib
import getpass
import sys
from pathlib import Path


class AISetup:
    """Class to setup AI configuration"""

    def __init__(self):
        self.config_file = "config.json"
        self.config = {}
        self.load_config()

    def load_config(self):
        """Load config from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                print("✅ Current configuration loaded")
            except Exception as e:
                print(f"❌ Error reading config file: {e}")
                self.config = {}
        else:
            self.config = {}

    def save_config(self):
        """Save config to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"❌ Error saving config: {e}")

    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def setup_gemini(self):
        """Setup Gemini API"""
        print("\n🤖 GOOGLE GEMINI SETUP")
        print("=" * 40)

        # Enter API key
        while True:
            api_key = getpass.getpass("Enter Gemini API Key (will be hashed): ").strip()
            if not api_key:
                print("❌ API key cannot be empty")
                continue

            if len(api_key) < 20:
                print("❌ API key too short, please check again")
                continue

            # Check basic format of Gemini API key
            if not api_key.startswith("AIza"):
                print("⚠️  Warning: API key does not start with 'AIza', may not be correct format")
                confirm = input("Do you want to continue? (y/N): ").lower().strip()
                if confirm != 'y':
                    continue

            break

        # Hash and save (only hash, not real key for security)
        hashed_key = self.hash_api_key(api_key)
        self.config.update({
            'gemini_api_key_hash': hashed_key
        })

        print("✅ Gemini API key configured")

        # Set environment variable for testing
        os.environ['GEMINI_API_KEY'] = api_key

        # Test API connection
        if self.test_gemini_api(api_key):
            print("🎉 Gemini setup completed successfully!")
        else:
            print("⚠️  Setup completed but API test failed. Please check your API key.")

    def test_gemini_api(self, api_key: str) -> bool:
        """Test Gemini API with a simple request"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')

            print("Testing Gemini API...")
            # Test with simple prompt
            response = model.generate_content("Say 'Hello World' in exactly 2 words.")
            if response and response.text:
                print("✅ API test successful!")
                return True
            return False
        except Exception as e:
            print(f"❌ Gemini API test failed: {str(e)}")
            return False

    def show_current_config(self):
        """Display current configuration"""
        if not self.config:
            print("❌ No configuration found")
            return

        print("\n📋 CURRENT CONFIGURATION")
        print("=" * 40)

        # Display Gemini status
        has_gemini = bool(self.config.get('gemini_api_key_hash')) or bool(os.getenv('GEMINI_API_KEY'))
        print(f"Google Gemini: {'✅ Configured' if has_gemini else '❌ Not configured'}")

    def main_menu(self):
        """Main menu"""
        while True:
            print("\n🚀 AI QUIZ ASSISTANT SETUP")
            print("=" * 40)
            print("1. Setup Google Gemini")
            print("2. View current configuration")
            print("3. Test API connection")
            print("4. Exit")

            choice = input("\nChoose (1-4): ").strip()

            if choice == '1':
                self.setup_gemini()
                self.save_config()
            elif choice == '2':
                self.show_current_config()
            elif choice == '3':
                api_key = os.getenv('GEMINI_API_KEY')
                if not api_key:
                    print("🔑 Gemini API key not found in environment variables.")
                    api_key = getpass.getpass("Enter Gemini API Key to test: ").strip()
                if api_key:
                    self.test_gemini_api(api_key)
                else:
                    print("❌ No API key provided")
            elif choice == '4':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")


def main():
    """Main function"""
    try:
        setup = AISetup()
        setup.main_menu()
    except KeyboardInterrupt:
        print("\n👋 Setup stopped")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
