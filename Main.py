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
import logging

# --- PAGE CONFIG ---
st.set_page_config(page_title="Auto Redial Web", page_icon="📞")
st.title("🚀 Auto Redial Pro (Web Edition)")

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

def init_driver():
    options = Options()
    options.add_argument("--headless")  # Must be headless on Streamlit
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- SIDEBAR / SETTINGS ---
with st.sidebar:
    st.header("Credentials")
    username = st.text_input("Username", value=st.session_state.get('user', ''))
    password = st.text_input("Password", type="password")
    env_choice = st.selectbox("Environment", list(ENVIRONMENTS.keys()))
    keywords = st.text_area("Keywords (comma separated)", value=st.session_state.get('kws', ''))
    
    if st.button("Save Settings"):
        st.session_state['user'] = username
        st.session_state['kws'] = keywords
        st.success("Settings saved for this session!")

# --- MAIN UI ---
col1, col2 = st.columns(2)
start_btn = col1.button("▶ START AUTOMATION", use_container_width=True)
stop_btn = col2.button("🛑 STOP", use_container_width=True)

status_container = st.empty()
log_container = st.empty()

if "running" not in st.session_state:
    st.session_state.running = False

if stop_btn:
    st.session_state.running = False
    st.warning("Stopping... Browser will close after current campaign.")

if start_btn:
    if not username or not password or not keywords:
        st.error("Please fill in all fields!")
    else:
        st.session_state.running = True
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        
        driver = None
        try:
            status_container.info("🔄 Initializing browser...")
            driver = init_driver()
            wait = WebDriverWait(driver, 15)
            
            while st.session_state.running and not is_past_stop_time():
                status_container.info(f"🌐 Logging into {env_choice}...")
                driver.get(ENVIRONMENTS[env_choice])

                # Login
                wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Username']"))).send_keys(username)
                wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Password']"))).send_keys(password)
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#normalLogin > button"))).click()
                time.sleep(3)

                # Navigation
                wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[1]/div/div/ul/li[3]"))).click()
                wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[1]/div/div/ul/li[3]/ul/li[2]/a"))).click()
                time.sleep(2)

                # Campaign Processing
                campaign_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/div[2]/div/div[1]/div/select")))
                options_data = driver.execute_script(
                    "return Array.from(arguments[0].options).map(option => ({value: option.value, text: option.text}));",
                    campaign_dropdown
                )

                matching = [opt for opt in options_data if any(kw in opt['text'] for kw in keyword_list)]
                
                for idx, opt in enumerate(matching):
                    if not st.session_state.running: break
                    
                    name = opt['text']
                    status_container.warning(f"🔎 Checking ({idx+1}/{len(matching)}): {name}")
                    
                    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));", campaign_dropdown, opt['value'])
                    time.sleep(2)

                    try:
                        dialed = int(wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div/small[1]/span"))).text.strip())
                        total = int(wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div/small[2]/span"))).text.strip())

                        if dialed >= total:
                            # Redial Action
                            driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/div[3]/div/div[2]/div/div[1]/button/div/div"))))
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/div[3]/div/div[2]/div/div[1]/div/div[2]/div/button[1]"))))
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/div[3]/div/div[2]/div/div[2]/button"))))
                            st.toast(f"✅ Redialed: {name}")
                    except Exception:
                        continue
                
                status_container.success("Cycle complete! Refreshing session in 5 seconds...")
                if driver: driver.quit()
                time.sleep(5)
                driver = init_driver() # Refresh browser for the next cycle

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if driver: driver.quit()
            st.session_state.running = False
            status_container.info("System Stopped.")
