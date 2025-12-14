import streamlit as st
import pymongo
import time
import pandas as pd

# --- 1. CONFIGURATION & CSS (AdminUX) ---
st.set_page_config(page_title="Aquench ERP", layout="wide")

# Custom CSS for White Sidebar, Navy Text, Orange Selection
st.markdown("""
    <style>
        /* Sidebar Background */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
        }
        /* Sidebar Text (Dark Navy) */
        [data-testid="stSidebar"] * {
            color: #001f3f;
            font-size: 16px;
        }
        /* Navigation Radio Buttons */
        div[role="radiogroup"] > label > div:first-of-type {
            display: none; /* Hide default radio circles */
        }
        div[role="radiogroup"] > label {
            background-color: #FFFFFF;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 5px;
            border: 1px solid #eee;
            transition: all 0.3s;
        }
        /* Hover State (Deep Blue) */
        div[role="radiogroup"] > label:hover {
            background-color: #001f3f !important;
            color: #FFFFFF !important;
        }
        /* Selected State (Orange) */
        div[role="radiogroup"] > label[data-selected="true"] {
            background-color: #FF851B !important;
            color: #FFFFFF !important;
            border-left: 5px solid #001f3f;
        }
        div[role="radiogroup"] > label[data-selected="true"] * {
             color: #FFFFFF !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. MONGODB CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        # Uses the manually fixed string in secrets.toml
        return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

client = init_connection()

# Stop if connection failed
if not client:
    st.stop()

db = client.my_erp_db  # Using your DB
users_collection = db.users

# --- 3. AUTHENTICATION LOGIC ---

def check_login(username, password):
    """Verifies credentials against MongoDB."""
    if not username or not password:
        return None
        
    user = users_collection.find_one({"username": username})
    
    # Simple password check (In production, hash passwords!)
    if user and user['password'] == password:
        return user
    return None

def init_session():
    """Initializes session state variables."""
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['user_name'] = None

init_session()

# --- 4. LOGIN PAGE ---
def login_page():
    # Center the login box
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 Aquench ERP Login")
        st.markdown("Please sign in to access your dashboard.")
        
        with st.form("login_form"):
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                user = check_login(username, password)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user_role'] = user['role']
                    st.session_state['user_name'] = user['name']
                    st.success(f"Welcome back, {user['name']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")

        st.write("---")
        
        # --- FIRST TIME SETUP (Expander) ---
        # Use this to create your first user, then you can remove this code block or hide it.
        with st.expander("⚠️ First Time Setup (Click Here)"):
            st.warning("Only use this if the database is empty.")
            new_user = st.text_input("New Admin Username")
            new_pass = st.text_input("New Password")
            if st.button("Create Admin User"):
                if new_user and new_pass:
                    # Check if user exists
                    if users_collection.find_one({"username": new_user}):
                        st.error("User already exists!")
                    else:
                        users_collection.insert_one({
                            "username": new_user.lower(),
                            "password": new_pass,
                            "role": "Admin",
                            "name": "Admin User"
                        })
                        st.success("User Created! You can now login.")
                else:
                    st.error("Please fill fields.")

# --- 5. MAIN APP (RBAC LOGIC) ---
def main_app():
    role = st.session_state['user_role']
    user_name = st.session_state['user_name']

    # --- Sidebar Logic based on Roles ---
    with st.sidebar:
        st.title("Aquench ERP")
        st.markdown(f"**User:** {user_name}")
        st.caption(f"Role: {role}")
        st.write("---")

        # Define Menu Options per Role
        menu_options = []
        
        if role == "Admin":
            menu_options = ["Dashboard", "Order Management", "Production", "Store", "Ecommerce", "User Mgmt"]
        elif role == "Production":
            menu_options = ["Dashboard", "Production"]
        elif role == "Store":
            menu_options = ["Dashboard", "Store"]
        elif role == "Ecommerce":
            menu_options = ["Dashboard", "Ecommerce"]
        
        # Default fallback
        if not menu_options:
            menu_options = ["Dashboard"]

        selection = st.radio("Navigate", menu_options)
        
        st.write("---")
        if st.button("Logout", type="primary"):
            st.session_state['logged_in'] = False
            st.session_state['user_role'] = None
            st.rerun()

    # --- Page Content Router ---
    if selection == "Dashboard":
        st.title("📊 Command Center")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Orders", "1,204", "+12%")
        col2.metric("Pending Dispatch", "45", "-2%")
        col3.metric("Production Queue", "12", "Normal")
        col4.metric("Returns", "3", "-1%")

    elif selection == "Order Management":
        st.title("📦 Order Management")
        st.info("Module Under Construction")

    elif selection == "Production":
        st.title("🏭 Production & Packing")
        st.write(f"Welcome {role}. Access Level: {role}")

    elif selection == "Store":
        st.title("🏪 Store Inventory")
        st.write("Live Stock Tracking")

    elif selection == "Ecommerce":
        st.title("🛒 Ecommerce Analytics")
        st.write("Sales Data")
    
    elif selection == "User Mgmt":
        st.title("👥 User Management")
        st.write("Admin panel to add/remove users.")
        
        # Simple User List for Admin
        if st.checkbox("Show All Users"):
            users = list(users_collection.find({}, {"_id": 0, "password": 0}))
            st.dataframe(users)

# --- 6. EXECUTION FLOW ---
if st.session_state['logged_in']:
    main_app()
else:
    login_page()
