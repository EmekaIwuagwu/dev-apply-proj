from playwright.sync_api import sync_playwright
from playwright_stealth import stealth

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            stealth(page)
            print("Successfully applied stealth to sync page")
        except Exception as e:
            print(f"Failed to apply stealth to sync page: {e}")
        browser.close()

if __name__ == "__main__":
    test()
