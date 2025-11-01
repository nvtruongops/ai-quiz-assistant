#!/usr/bin/env python3
"""
AI Quiz Assistant Setup Script
Configure AI provider (Gemini or AWS Bedrock) and credentials
"""

import os
import json
import hashlib
import getpass
import sys
from pathlib import Path
import time


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
            'ai_provider': 'gemini',
            'gemini_api_key_hash': hashed_key
            # Note: Real API key is not stored in config for security
        })

        print("✅ Gemini API key configured")

        # Test API connection
        if self.test_api_connection():
            print("🎉 Gemini setup completed successfully!")
        else:
            print("⚠️  Setup completed but API test failed. You can still use the app, but please check your API key.")

    def setup_bedrock(self):
        """Setup AWS Bedrock"""
        print("\n☁️  AWS BEDROCK SETUP")
        print("=" * 40)

        # Enter AWS Region
        while True:
            region = input("Enter AWS Region (default: us-east-1): ").strip()
            if not region:
                region = "us-east-1"
            break

        # Enter AWS Access Key ID
        while True:
            access_key = getpass.getpass("Enter AWS Access Key ID: ").strip()
            if not access_key:
                print("❌ Access Key ID cannot be empty")
                continue
            break

        # Enter AWS Secret Access Key
        while True:
            secret_key = getpass.getpass("Enter AWS Secret Access Key: ").strip()
            if not secret_key:
                print("❌ Secret Access Key cannot be empty")
                continue
            break

        # Save config
        self.config.update({
            'ai_provider': 'bedrock',
            'aws_region': region,
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key
        })

        print("✅ AWS Bedrock credentials configured")

        # Test API connection
        if self.test_api_connection():
            print("🎉 AWS Bedrock setup completed successfully!")
        else:
            print("⚠️  Setup completed but API test failed. You can still use the app, but please check your AWS credentials.")

    def test_gemini_api(self, api_key: str) -> bool:
        """Test Gemini API with a simple request"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')

            # Test with simple prompt
            response = model.generate_content("Say 'Hello World' in exactly 2 words.")
            if response and response.text and "Hello World" in response.text.strip():
                return True
            return False
        except Exception as e:
            print(f"❌ Gemini API test failed: {str(e)}")
            return False

    def test_bedrock_api(self, region: str) -> bool:
        """Test AWS Bedrock API with a simple request"""
        try:
            import boto3
            client = boto3.client('bedrock-runtime', region_name=region)

            # Test with simple prompt
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Say 'Hello World' in exactly 2 words."
                            }
                        ]
                    }
                ]
            }

            response = client.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            if content and "Hello World" in content[0].get('text', ''):
                return True
            return False

        except Exception as e:
            print(f"❌ Bedrock API test failed: {str(e)}")
            return False

    def test_api_connection(self):
        """Test API connection after setup"""
        provider = self.config.get('ai_provider', 'gemini')

        print(f"\n🧪 TESTING {provider.upper()} API CONNECTION...")
        print("=" * 50)

        success = False

        if provider == 'gemini':
            # Get API key from environment or prompt user
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("🔑 Gemini API key not found in environment variables.")
                api_key = getpass.getpass("Enter Gemini API Key to test: ").strip()
                if not api_key:
                    print("❌ No API key provided")
                    return False
            
            print("Testing Gemini API...")
            success = self.test_gemini_api(api_key)

        elif provider == 'bedrock':
            region = self.config.get('aws_region', 'us-east-1')
            print(f"Testing AWS Bedrock API (region: {region})...")
            success = self.test_bedrock_api(region)

        if success:
            print("✅ API test successful! Configuration is working.")
            return True
        else:
            print("❌ API test failed. Please check your configuration.")
            return False

    def setup_both_providers(self):
        """Setup both Gemini and Bedrock"""
        print("\n🤖☁️  SETUP BOTH PROVIDERS")
        print("=" * 50)
        
        # Setup Gemini first
        print("\n--- SETUP GEMINI ---")
        self.setup_gemini()
        
        # Setup Bedrock second
        print("\n--- SETUP BEDROCK ---")
        self.setup_bedrock()
        
        # Set default provider to Gemini
        self.config['ai_provider'] = 'gemini'
        
        print("\n🎉 Both providers setup completed!")
        print("💡 Default uses Gemini. Use Alt+S to switch to Bedrock.")
        
        self.save_config()

    def switch_provider(self):
        """Switch between Gemini and Bedrock"""
        if not self.config:
            print("❌ No configuration found. Please run setup first.")
            return

        current = self.config.get('ai_provider', 'unknown')
        print(f"\n🔄 SWITCH AI PROVIDER")
        print(f"Current provider: {current.upper()}")

        # Check if both providers have been setup
        has_gemini = bool(self.config.get('gemini_api_key_hash')) or bool(os.getenv('GEMINI_API_KEY'))
        has_bedrock = bool(self.config.get('aws_access_key_id') and self.config.get('aws_secret_access_key'))

        if current == 'gemini':
            if not has_bedrock:
                print("❌ AWS Bedrock not configured.")
                print("💡 Run option 2 to setup AWS Bedrock first.")
                return
            self.config['ai_provider'] = 'bedrock'
            print("✅ Switched to AWS Bedrock")
        elif current == 'bedrock':
            if not has_gemini:
                print("❌ Google Gemini not configured.")
                print("💡 Run option 1 to setup Google Gemini first.")
                return
            self.config['ai_provider'] = 'gemini'
            print("✅ Switched to Google Gemini")
        else:
            print("❌ Unknown provider")

        self.save_config()

    def show_current_config(self):
        """Display current configuration"""
        if not self.config:
            print("❌ No configuration found")
            return

        print("\n📋 CURRENT CONFIGURATION")
        print("=" * 40)
        print(f"AI Provider in use: {self.config.get('ai_provider', 'unknown').upper()}")

        # Display Gemini status
        has_gemini = bool(self.config.get('gemini_api_key_hash')) or bool(os.getenv('GEMINI_API_KEY'))
        print(f"Google Gemini: {'✅ Configured' if has_gemini else '❌ Not configured'}")

        # Display Bedrock status
        has_bedrock = bool(self.config.get('aws_access_key_id') and self.config.get('aws_secret_access_key'))
        region = self.config.get('aws_region', 'unknown')
        print(f"AWS Bedrock: {'✅ Configured' if has_bedrock else '❌ Not configured'}")
        if has_bedrock:
            print(f"  Region: {region}")

    def main_menu(self):
        """Main menu"""
        while True:
            print("\n🚀 AI QUIZ ASSISTANT SETUP")
            print("=" * 40)
            print("1. Setup Google Gemini")
            print("2. Setup AWS Bedrock")
            print("3. View current configuration")
            print("4. Switch AI Provider")
            print("5. Exit")

            choice = input("\nChoose (1-5): ").strip()

            if choice == '1':
                self.setup_gemini()
                self.save_config()
            elif choice == '2':
                self.setup_bedrock()
                self.save_config()
            elif choice == '3':
                self.show_current_config()
            elif choice == '4':
                self.switch_provider()
            elif choice == '5':
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