"""
Automated Streamlit Cloud Deployment
Uses Playwright to automate the deployment process
"""

from playwright.sync_api import sync_playwright
import time

# Configuration
REPO = "SCEVLTD/BrandedAI"
BRANCH = "liquidline-deploy"
MAIN_FILE = "app.py"

def deploy_to_streamlit():
    print("=" * 60)
    print("LIQUIDLINE BANK AUTOMATION - AUTOMATED DEPLOYMENT")
    print("=" * 60)
    print()

    with sync_playwright() as p:
        # Launch browser in headed mode
        print("Launching browser...")
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # Go to Streamlit Cloud
        print("Navigating to Streamlit Cloud...")
        page.goto("https://share.streamlit.io")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Step 1: Click "Continue to sign-in" button
        print("Looking for 'Continue to sign-in' button...")
        signin_btn = page.locator('button:has-text("Continue to sign-in")')

        if signin_btn.count() > 0:
            print("Clicking 'Continue to sign-in'...")
            signin_btn.first.click()
            time.sleep(3)

        # Step 2: Click "Continue with GitHub" button
        print("Looking for 'Continue with GitHub' button...")
        github_btn = page.locator('button:has-text("Continue with GitHub")')

        if github_btn.count() > 0:
            print("Clicking 'Continue with GitHub'...")
            github_btn.first.click()
            time.sleep(3)

            page.screenshot(path="streamlit_github_auth.png")
            print("Screenshot: streamlit_github_auth.png")

            # Wait for GitHub OAuth or dashboard
            print()
            print("=" * 60)
            print("GITHUB AUTHENTICATION")
            print("=" * 60)
            print("Please complete GitHub authentication in the browser.")
            print("If prompted, authorize Streamlit to access your repos.")
            print("Waiting up to 2 minutes for authentication...")
            print("=" * 60)

            try:
                # Wait for dashboard (2 minutes)
                page.wait_for_selector(
                    'button:has-text("New app"), button:has-text("Create app"), [data-testid="workspaces"]',
                    timeout=120000
                )
                print("Authentication successful!")
            except:
                print("Still waiting for auth...")

        time.sleep(3)
        page.screenshot(path="streamlit_dashboard.png")
        print("Screenshot: streamlit_dashboard.png")

        # Step 3: Look for "New app" or "Create app" button
        print("Looking for 'New app' button...")
        new_app_btn = page.locator('button:has-text("New app"), button:has-text("Create app")')

        if new_app_btn.count() > 0:
            print("Clicking 'New app'...")
            new_app_btn.first.click()
            time.sleep(3)
            page.screenshot(path="streamlit_new_app_form.png")
            print("Screenshot: streamlit_new_app_form.png")

        print()
        print("=" * 60)
        print("DEPLOYMENT READY")
        print("=" * 60)
        print()
        print("In the browser, configure your app:")
        print(f"  Repository: {REPO}")
        print(f"  Branch: {BRANCH}")
        print(f"  Main file: {MAIN_FILE}")
        print()
        print("Click 'Deploy!' when ready.")
        print()
        print("After deployment, go to App Settings > Secrets:")
        print('  OPENROUTER_API_KEY = "sk-or-v1-your-key"')
        print('  APP_PASSWORD = "your-password"')
        print('  CLIENT_NAME = "Liquidline"')
        print('  PRIMARY_COLOR = "#1E88E5"')
        print('  FEATURE_AI_MATCHING = "true"')
        print('  FEATURE_REMITTANCE = "true"')
        print()
        print("Browser will stay open. Press Ctrl+C when done.")
        print("=" * 60)

        # Keep browser open for user interaction
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nClosing browser...")

        browser.close()

if __name__ == "__main__":
    deploy_to_streamlit()
