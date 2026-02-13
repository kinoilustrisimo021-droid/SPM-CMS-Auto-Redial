import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import time
import pytz
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Auto Redial Pro", page_icon="📞")
st.title("🚀 Auto Redial Pro (Local Edition)")
st.markdown("### Running on your local network to bypass Sophos/VPN restrictions.")

# Environments
ENVIRONMENTS = {
    "Environment 1": "https://texxen-voliapp.spmadridph.com/admin",
    "Environment 2": "https://texxen-voliappe2.spmadridph.com/admin",
    "Environment 3": "https://texxen-voliappe3.spmadridph.com/admin",
    "Environment 4": "https://texxen-voliappe4.spmadridph.com/admin",
    "Environment 5": "https://texxen-voliappe5.spmadridph.com/admin",
}

# --- HELPER FUNCTIONS ---
def is_past_stop_time():
    ph_tz = pytz.timezone('Asia/Manila')
    return datetime.now(ph_tz).hour >= 21

def init_driver(use_headless):
    options = Options()
    if use_headless:
        options.add_argument("--headless")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # This helps bypass some basic firewall bot-detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- SESSION STATE ---
if "running" not in st.session_state: st.session_state.running = False

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    username = st.text_input("Username", value=st.session_state.get('user', ''))
    password = st.text_input("Password", type="password")
    env_choice = st.selectbox("Environment", list(ENVIRONMENTS.keys()))
    keywords = st.text_area("Keywords (comma separated)", value=st.session_state.get('kws', ''))
    
    st.divider()
    headless_mode = st.checkbox("Run in Background (Headless)", value=False)
    st.info("💡 Turn OFF 'Background mode' if you need to see the Sophos login page.")
    
    if st.button("Save Settings"):
        st.session_state['user'] = username
        st.session_state['kws'] = keywords
        st.success("Settings saved locally!")

# --- MAIN UI ---
col1, col2 = st.columns(2)
start_btn = col1.button("▶ START AUTOMATION", use_container_width=True)
stop_btn = col2.button("🛑 STOP", use_container_width=True)

status_container = st.empty()

if stop_btn:
    st.session_state.running = False
    st.warning("Stop signal received.")

if start_btn:
    if not username or not password or not keywords:
        st.error("Please fill in all credentials!")
    else:
        st.session_state.running = True
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        
        driver = None
        try:
            status_container.info("🔄 Launching Local Chrome...")
            driver = init_driver(headless_mode)
            wait = WebDriverWait(driver, 20)
            
            while st.session_state.running:
                if is_past_stop_time():
                    st.warning("Automatic stop at 9:00 PM Manila Time.")
                    break

                status_container.info(f"🌐 Accessing {env_choice} via your network...")
                try:
                    driver.get(ENVIRONMENTS[env_choice])
                except Exception as e:
                    st.error(f"Cannot reach site. Ensure your VPN/Sophos is active on this PC. Error: {e}")
                    break

                # Login Sequence
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username']"))).send_keys(username)
                    driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(password)
                    driver.find_element(By.CSS_SELECTOR, "#normalLogin > button").click()
                    time.sleep(3)
                    
                    # Navigate to Campaigns
                    wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[1]/div/div/ul/li[3]"))).click()
                    wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[1]/div/div/ul/li[3]/ul/li[2]/a"))).click()
                    time.sleep(2)
                except Exception as e:
                    st.error("Login failed. Site might be slow or layout changed.")
                    break

                # Process Campaigns
                dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/div[2]/div/div[1]/div/select")))
                options = driver.execute_script(
                    "return Array.from(arguments[0].options).map(o => ({value: o.value, text: o.text}));", dropdown
                )

                matching = [o for o in options if any(kw.lower() in o['text'].lower() for kw in keyword_list)]
                
                for idx, opt in enumerate(matching):
                    if not st.session_state.running: break
                    
                    status_container.warning(f"🔎 Checking ({idx+1}/{len(matching)}): {opt['text']}")
                    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));", dropdown, opt['value'])
                    time.sleep(2)

                    try:
                        dialed = int(wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div/small[1]/span"))).text.strip())
                        total = int(wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div/small[2]/span"))).text.strip())

                        if dialed >= total and total > 0:
                            # Execute Redial
                            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "/html/body/div[2]/div[2]/div/div[3]/div/div[2]/div/div[1]/button/div/div"))
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "/html/body/div[2]/div[2]/div/div[3]/div/div[2]/div/div[1]/div/div[2]/div/button[1]"))
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "/html/body/div[2]/div[2]/div/div[3]/div/div[2]/div/div[2]/button"))
                            st.toast(f"✅ Redialed: {opt['text']}")
                    except:
                        continue
                
                status_container.success("Cycle complete. Cooling down for 60 seconds...")
                time.sleep(60)
                driver.refresh()

        except Exception as e:
            st.error(f"System Error: {e}")
        finally:
            if driver: driver.quit()
            st.session_state.running = False
            status_container.info("Automation Stopped.")
