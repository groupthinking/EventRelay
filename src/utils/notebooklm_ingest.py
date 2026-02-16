import os
import sys
import time
from playwright.sync_api import sync_playwright

# Configuration
# Use a local profile to avoid conflicts with the running MCP server
USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "notebooklm_profile_v2")
NOTEBOOKLM_URL = "https://notebooklm.google.com/"

def upload_to_notebooklm(file_path):
    """
    Uploads a file to a new NotebookLM notebook using a dedicated Chrome profile.
    Returns the new notebook URL.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None

    print(f"Starting NotebookLM ingestion for: {file_path}")
    
    with sync_playwright() as p:
        context = None
        browser = None
        try:
            # Try connecting to existing browser first (CDP)
            try:
                print("Attempting to connect to existing Chrome instance on port 9222...")
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                print("Successfully connected to existing browser!")
            except Exception as e:
                print(f"Could not connect to existing browser: {e}")
                print("Falling back to launching new persistent context...")

            if not context:
                # Launch persistent context
                # We use headless=False so the user can see/interact if needed (especially for first login)
                print(f"Launching browser with profile: {USER_DATA_DIR}")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    headless=False, # Must be false to allow login interaction
                    accept_downloads=True,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-infobars",
                    ],
                    ignore_default_args=["--enable-automation"],
                )
            
            if len(context.pages) > 0:
                page = context.pages[0]
            else:
                page = context.new_page()
            
            print("Navigating to NotebookLM...")
            page.goto(NOTEBOOKLM_URL)
            
            # Check for login
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass

            if "accounts.google.com" in page.url or page.locator("text=Sign in").count() > 0 or page.locator("text=Try NotebookLM").count() > 0:
                print("\n" + "="*60)
                print("ACTION REQUIRED: Please log in to Google NotebookLM in the opened browser window.")
                print("We are using a secure browser session to avoid security checks.")
                print("Once you are logged in and see your notebook dashboard, the script will continue.")
                print("="*60 + "\n")
                
                # Wait for user to log in. We check periodically if we are on the dashboard.
                logged_in = False
                
                print("Waiting for login (looking for 'New Notebook' or 'Create' button)...")
                for i in range(120): # Wait up to 10 minutes (120 * 5s)
                    try:
                        if "accounts.google.com" not in page.url:
                            if page.locator("text=New Notebook").count() > 0:
                                logged_in = True
                                print("\nFound 'New Notebook' button.")
                                break
                            elif page.locator("button:has-text('Create')").count() > 0:
                                logged_in = True
                                print("\nFound 'Create' button.")
                                break
                            elif page.locator(".notebook-card.new").count() > 0:
                                logged_in = True
                                print("\nFound 'New' card.")
                                break
                    except:
                        pass
                    
                    if i % 5 == 0:
                        try:
                            sys.stdout.write(f". ({page.url})")
                        except:
                            sys.stdout.write(".")
                        sys.stdout.flush()
                    time.sleep(5)
                
                print("") # Newline
                if not logged_in:
                    print("Error: Login timeout or not completed.")
                    context.close()
                    return None
            
            # Click "New Notebook"
            try:
                print("Clicking creation button...")
                # We already waited in the loop above, so we can try clicking directly.
                if page.locator("text=New Notebook").count() > 0:
                     page.click("text=New Notebook")
                elif page.locator("button:has-text('Create')").count() > 0:
                     page.locator("button:has-text('Create')").first.click()
                else:
                     page.locator(".notebook-card.new").click()
            except Exception as e:
                print(f"Error clicking creation button: {e}")
                context.close()
                return None

            print("Waiting for notebook to be created...")
            # Wait for URL to change from "creating" to actual ID
            page.wait_for_url(lambda u: "/notebook/" in u and "/creating" not in u, timeout=30000)
            notebook_url = page.url
            print(f"Created Notebook: {notebook_url}")
            
            print("Uploading source...")
            # Handling the upload
            try:
                # Check if we need to click "Add source" or a specific source type
                # Sometimes the panel is already open, sometimes not.
                
                # Wait for the page to settle
                page.wait_for_load_state("networkidle", timeout=5000)

                # If "Add source" button is visible (meaning panel might be closed), click it
                if page.locator("text=Add source").is_visible():
                    print("Clicking 'Add source' button...")
                    page.click("text=Add source")
                    time.sleep(1)

                # Try to trigger file chooser by clicking likely buttons
                print("Attempting to trigger file chooser...")
                
                upload_triggers = [
                    "text=Upload a source",
                    "text=PDF",
                    "text=Text file",
                    "button:has-text('Upload')",
                    "div[role='button']:has-text('Upload')",
                    "text=Upload"
                ]
                
                file_chooser = None
                for trigger in upload_triggers:
                    try:
                        loc = page.locator(trigger).first
                        if loc.is_visible():
                            print(f"Trying upload trigger: {trigger}")
                            with page.expect_file_chooser(timeout=3000) as fc_info:
                                loc.click()
                            file_chooser = fc_info.value
                            print("File chooser triggered!")
                            break
                    except Exception:
                        # expected if click doesn't trigger chooser
                        pass
                
                if file_chooser:
                    print(f"Uploading file: {file_path}")
                    file_chooser.set_files(file_path)
                else:
                    # Fallback to looking for input directly if no chooser triggered
                    print("No file chooser triggered. Looking for input[type='file']...")
                    page.wait_for_selector('input[type="file"]', state="attached", timeout=5000)
                    page.set_input_files('input[type="file"]', file_path)
            except Exception as e:
                print(f"Error uploading file: {e}")
                # Try to capture what might be wrong
                try:
                    print(f"Current URL: {page.url}")
                    # Save HTML to file for inspection
                    with open("debug_notebooklm_page.html", "w", encoding="utf-8") as f:
                        f.write(page.content())
                    print("Saved page content to debug_notebooklm_page.html")
                except:
                    pass
                context.close()
                return None

            print("Waiting for source processing...")
            file_name = os.path.basename(file_path)
            display_name = os.path.splitext(file_name)[0]
            
            # Wait for the source to appear in the list
            try:
                page.wait_for_selector(f"text={display_name}", timeout=60000)
                print("Source successfully added.")
            except:
                print("Warning: Timed out waiting for source to appear in list.")

            # Give it a moment to sync/save
            time.sleep(3)
            
            context.close()
            return notebook_url

        except Exception as e:
            print(f"An error occurred: {e}")
            if 'context' in locals():
                context.close()
            return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python notebooklm_ingest.py <file_path>")
        sys.exit(1)
        
    fpath = sys.argv[1]
    url = upload_to_notebooklm(fpath)
    if url:
        print(f"SUCCESS: {url}")
    else:
        sys.exit(1)