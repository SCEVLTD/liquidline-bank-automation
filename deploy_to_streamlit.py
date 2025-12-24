"""
Streamlit Cloud Deployment Helper
Opens browser to deploy the Liquidline Bank Automation app

Run: python deploy_to_streamlit.py
"""

import webbrowser
import time

# Deployment configuration
REPO = "SCEVLTD/BrandedAI"
BRANCH = "liquidline-deploy"
MAIN_FILE = "app.py"

print("=" * 60)
print("LIQUIDLINE BANK AUTOMATION - STREAMLIT CLOUD DEPLOYMENT")
print("=" * 60)
print()
print("Deployment Configuration:")
print(f"  Repository: {REPO}")
print(f"  Branch: {BRANCH}")
print(f"  Main file: {MAIN_FILE}")
print()

# Direct deploy URL (if logged in to Streamlit Cloud)
deploy_url = f"https://share.streamlit.io/deploy?repository={REPO}&branch={BRANCH}&mainModule={MAIN_FILE}"

print("Opening Streamlit Cloud deployment page...")
print()
webbrowser.open("https://share.streamlit.io")

print("=" * 60)
print("DEPLOYMENT STEPS:")
print("=" * 60)
print()
print("1. Sign in with your GitHub account (SCEVLTD)")
print()
print("2. Click 'New app' button")
print()
print("3. Configure the app:")
print(f"   - Repository: {REPO}")
print(f"   - Branch: {BRANCH}")
print(f"   - Main file path: {MAIN_FILE}")
print()
print("4. Click 'Deploy!'")
print()
print("5. Once deployed, go to App Settings > Secrets and add:")
print()
print('   OPENROUTER_API_KEY = "sk-or-v1-your-key"')
print('   APP_PASSWORD = "your-secure-password"')
print('   CLIENT_NAME = "Liquidline"')
print('   PRIMARY_COLOR = "#1E88E5"')
print('   FEATURE_AI_MATCHING = "true"')
print('   FEATURE_REMITTANCE = "true"')
print()
print("=" * 60)
print("Your app URL will be: https://scevltd-brandedai-app-xxxxx.streamlit.app")
print("=" * 60)
