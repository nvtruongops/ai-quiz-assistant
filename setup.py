#!/usr/bin/env python3
"""
AI Quiz Assistant - Setup & Configuration Wizard
- Install & update Python dependencies
- Configure Google Gemini AI Studio with dynamic model fetching & selection
- Configure Custom OpenAI-compatible Provider (Ollama, LM Studio, vLLM, Proxies) with dynamic model fetching & selection
- Launch GUI Setup Wizard
"""

import os
import sys
import getpass
import argparse
import subprocess
from pathlib import Path

# Set project root and add src to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'), override=True)


def install_requirements():
    """Install or upgrade Python dependencies from requirements.txt"""
    print("=" * 60)
    print("📦 INSTALLING / UPDATING PYTHON DEPENDENCIES")
    print("=" * 60)
    req_path = os.path.join(PROJECT_ROOT, 'requirements.txt')
    if not os.path.exists(req_path):
        print(f"❌ Error: {req_path} not found!")
        return False

    print(f"Running: {sys.executable} -m pip install -r requirements.txt\n")
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            check=True
        )
        print("\n✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error installing dependencies: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def save_env(key: str, val: str):
    """Save or update environment variable in .env file"""
    env_path = os.path.join(PROJECT_ROOT, '.env')
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={val}\n"
            found = True
            break

    if not found:
        lines.append(f"{key}={val}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    os.environ[key] = val


def setup_gemini():
    """Configure Google Gemini AI Studio with dynamic model retrieval & selection"""
    print("\n" + "=" * 60)
    print("🤖 CONFIGURE GOOGLE GEMINI AI STUDIO")
    print("=" * 60)
    print("Get your free API key at: https://aistudio.google.com/app/apikey\n")

    current_key = os.getenv('GEMINI_API_KEY', '')
    if current_key:
        print(f"Current API Key: {current_key[:8]}...{current_key[-4:]}")
        use_curr = input("Keep current key? [Y/n]: ").strip().lower()
        if use_curr == 'n':
            api_key = getpass.getpass("Enter new Gemini API Key: ").strip()
        else:
            api_key = current_key
    else:
        api_key = getpass.getpass("Enter Gemini API Key: ").strip()

    if not api_key:
        print("❌ API key cannot be empty!")
        return False

    # Fetch available models dynamically via API
    print("\n⏳ Fetching available Gemini models for your API key...")
    try:
        from gemini_client import GeminiAPIClient
    except ImportError:
        from src.gemini_client import GeminiAPIClient

    ok, models, msg = GeminiAPIClient.list_models(api_key, timeout=12)
    selected_model = ""

    if ok and models:
        print(f"\n📋 Found {len(models)} available models:")
        for idx, m_name in enumerate(models, 1):
            print(f"  [{idx:2d}] {m_name}")
        print("  [ C] Enter custom model name manually")

        choice = input(f"\nSelect a model [1-{len(models)} or C, default 1: {models[0]}]: ").strip()
        if choice.lower() == 'c':
            selected_model = input("Enter custom Gemini model name: ").strip()
        elif choice.isdigit() and 1 <= int(choice) <= len(models):
            selected_model = models[int(choice) - 1]
        else:
            selected_model = models[0]
    else:
        print(f"⚠️ Could not load models automatically ({msg}).")
        selected_model = input("Enter Gemini model name manually [e.g. gemini-3.1-flash-lite]: ").strip()
        if not selected_model:
            selected_model = "gemini-3.1-flash-lite"

    # Connection Test
    print(f"\n⏳ Testing connection with model '{selected_model}'...")
    try:
        client = GeminiAPIClient(api_key=api_key, model_name=selected_model)
        test_ok, test_msg, lat = client.test_connection()
        if test_ok:
            print(f"✅ {test_msg} ({lat:.2f}s latency)")
        else:
            print(f"⚠️ Connection test failed: {test_msg}")
            cont = input("Do you still want to save this configuration? (y/N): ").lower().strip()
            if cont != 'y':
                return False
    except Exception as e:
        print(f"⚠️ Error testing API: {e}")

    # Save to .env
    save_env('API_PROVIDER', 'gemini')
    save_env('GEMINI_API_KEY', api_key)
    save_env('GEMINI_MODEL', selected_model)

    try:
        from settings_manager import SettingsManager
    except ImportError:
        from src.settings_manager import SettingsManager
    sm = SettingsManager()
    sm.settings['setup_completed'] = True
    sm.save_settings()

    print("\n🎉 Google Gemini configuration saved successfully!")
    print(f"Active Provider: gemini | Model: {selected_model}")
    return True


def setup_custom():
    """Configure Custom Local / Proxy Provider with dynamic model retrieval & selection"""
    print("\n" + "=" * 60)
    print("🏠 CONFIGURE CUSTOM LOCAL / OPENAI-COMPATIBLE PROVIDER")
    print("=" * 60)

    cur_url = (os.getenv('CUSTOM_API_URL') or '').strip() or 'http://localhost:11434/v1'
    url = input(f"Enter API Endpoint URL [default: {cur_url}]: ").strip()
    if not url:
        url = cur_url

    cur_key = os.getenv('CUSTOM_API_KEY', '')
    key_prompt = "Enter API Key (optional for local, required for proxy)"
    if cur_key:
        key_prompt += f" [keep current: {cur_key[:6]}...]"
    key_prompt += ": "

    raw_key = getpass.getpass(key_prompt).strip()
    key = raw_key if raw_key else cur_key

    # Dynamically fetch available models from the custom endpoint
    print(f"\n⏳ Checking endpoint '{url}' and querying available models...")
    try:
        from custom_client import CustomAPIClient
    except ImportError:
        from src.custom_client import CustomAPIClient

    ok, models, msg = CustomAPIClient.list_models(url, key, timeout=8)
    selected_model = ""

    if ok and models:
        print(f"\n📋 Found {len(models)} models at this endpoint:")
        for idx, m_name in enumerate(models, 1):
            print(f"  [{idx:2d}] {m_name}")
        print("  [ C] Enter custom model name manually")

        choice = input(f"\nSelect a model [1-{len(models)} or C, default 1: {models[0]}]: ").strip()
        if choice.lower() == 'c':
            selected_model = input("Enter custom model name: ").strip()
        elif choice.isdigit() and 1 <= int(choice) <= len(models):
            selected_model = models[int(choice) - 1]
        else:
            selected_model = models[0]
    else:
        print(f"⚠️ Could not load models automatically ({msg}).")
        cur_model = os.getenv('CUSTOM_MODEL', '')
        default_prompt = f" [default: {cur_model}]" if cur_model else ""
        selected_model = input(f"Enter model name manually{default_prompt}: ").strip()
        if not selected_model and cur_model:
            selected_model = cur_model

    if not selected_model:
        selected_model = "llama3.2-vision"

    # Test Connection
    print(f"\n⏳ Testing Custom API connection with model '{selected_model}'...")
    try:
        client = CustomAPIClient(api_url=url, api_key=key, model=selected_model)
        test_ok, test_msg, lat = client.test_connection()
        if test_ok:
            print(f"✅ {test_msg} ({lat:.2f}s latency)")
        else:
            print(f"⚠️ Connection test failed: {test_msg}")
            cont = input("Do you still want to save this configuration? (y/N): ").lower().strip()
            if cont != 'y':
                return False
    except Exception as e:
        print(f"⚠️ Error testing API: {e}")

    # Save to .env
    save_env('API_PROVIDER', 'custom')
    save_env('CUSTOM_API_URL', url)
    save_env('CUSTOM_API_KEY', key)
    save_env('CUSTOM_MODEL', selected_model)

    try:
        from settings_manager import SettingsManager
    except ImportError:
        from src.settings_manager import SettingsManager
    sm = SettingsManager()
    sm.settings['setup_completed'] = True
    sm.save_settings()

    print("\n🎉 Custom Provider configuration saved successfully!")
    print(f"Active Provider: custom | Endpoint: {url} | Model: {selected_model}")
    return True


def launch_gui_setup():
    """Launch the Graphical Initial Setup Wizard"""
    print("\n🖥️ Launching GUI Setup Wizard...")
    try:
        from settings_manager import show_initial_setup_dialog, SettingsManager
        from config_manager import ConfigManager
    except ImportError:
        from src.settings_manager import show_initial_setup_dialog, SettingsManager
        from src.config_manager import ConfigManager

    cm = ConfigManager()
    sm = SettingsManager()
    ok = show_initial_setup_dialog(config_manager=cm, settings_manager=sm)
    if ok:
        sm.settings['setup_completed'] = True
        sm.save_settings()
        print("✅ GUI Setup completed successfully!")
    else:
        print("ℹ️ GUI Setup closed without changes.")
    return ok


def setup_wizard_menu():
    """Interactive CLI menu"""
    while True:
        print("\n" + "=" * 60)
        print("🎯 AI QUIZ ASSISTANT - SETUP & CONFIGURATION")
        print("=" * 60)
        print("1. Install / Update Python Requirements (pip install -r requirements.txt)")
        print("2. Configure Google Gemini AI Studio (Dynamic Model Fetching)")
        print("3. Configure Custom Provider (Ollama/vLLM/LM Studio - Dynamic Model Fetching)")
        print("4. Launch Graphical Setup Wizard (GUI)")
        print("5. Full Setup (Install Dependencies + Configure AI)")
        print("6. Exit")
        print("-" * 60)

        choice = input("Select an option [1-6]: ").strip()
        if choice == '1':
            install_requirements()
        elif choice == '2':
            setup_gemini()
        elif choice == '3':
            setup_custom()
        elif choice == '4':
            launch_gui_setup()
        elif choice == '5':
            if install_requirements():
                prov = input("\nSelect Provider to configure (1=Gemini, 2=Custom): ").strip()
                if prov == '2':
                    setup_custom()
                else:
                    setup_gemini()
        elif choice in ('6', 'q', 'exit'):
            print("Setup wizard exited.")
            break
        else:
            print("Invalid choice, please select between 1 and 6.")


def main():
    parser = argparse.ArgumentParser(description="AI Quiz Assistant Setup & Configuration Tool")
    parser.add_argument("--install-deps", "--install-requirements", "-i", action="store_true",
                        help="Install or upgrade dependencies from requirements.txt only")
    parser.add_argument("--setup-ai", "-a", action="store_true",
                        help="Configure AI Provider credentials & models only")
    parser.add_argument("--gui", "-g", action="store_true",
                        help="Launch the Graphical Setup Wizard")
    parser.add_argument("--all", action="store_true",
                        help="Run full setup (install dependencies then configure AI)")

    args = parser.parse_args()

    if args.install_deps:
        success = install_requirements()
        sys.exit(0 if success else 1)
    elif args.setup_ai:
        print("\nSelect AI Provider to configure:")
        print("1. Google Gemini AI Studio")
        print("2. Custom OpenAI-compatible Provider")
        c = input("Choice [1/2]: ").strip()
        if c == '2':
            setup_custom()
        else:
            setup_gemini()
    elif args.gui:
        launch_gui_setup()
    elif args.all:
        if install_requirements():
            setup_gemini()
    else:
        setup_wizard_menu()


if __name__ == "__main__":
    main()
