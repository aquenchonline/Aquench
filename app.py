import streamlit as st
import pymongo
import time
import pandas as pd
import datetime

# --- 1. CONFIGURATION & CSS (AdminUX) ---
st.set_page_config(page_title="Aquench ERP", layout="wide")

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
        return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

client = init_connection()

if not client:
    st.stop()

db = client.my_erp_db
users_collection = db.users
tasks_collection = db.production_tasks

# --- 3. AUTO-SETUP USERS (Background Script) ---
def setup_initial_users():
    """Ensures the requested users exist in the database."""
    # List of users to ensure exist
    required_users = [
        {"username": "production", "password": "Amavik@80", "role": "Production", "name": "Production Incharge"},
        {"username": "packing", "password": "Amavik@97", "role": "Packing", "name": "Packing Incharge"},
        {"username": "store", "password": "Amavik@17", "role": "Store", "name": "Store Manager"},
        {"username": "ecommerce", "password": "Amavik@12", "role": "Ecommerce", "name": "Ecom Manager"},
        {"username": "amar", "password": "Aquench@1933", "role": "Admin", "name": "Amar (Admin)"}
    ]

    for user in required_users:
        # Check if username exists
        if not users_collection.find_one({"username": user["username"]}):
            users_collection.insert_one(user)
            print(f"✅ Created user: {user['username']}")

# Run setup once
setup_initial_users()

# --- 4. AUTHENTICATION LOGIC ---

def check_login(username, password):
    if not username or not password:
        return None
    
    # Case insensitive username search
    user = users_collection.find_one({"username": username.lower()})
    
    if user and user['password'] == password:
        return user
    return None

def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['user_name'] = None

init_session()

# --- 5. LOGIN PAGE ---
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 Aquench ERP")
        st.markdown("##### Authorized Access Only")
        
        with st.form("login_form"):
            username = st.text_input("User ID")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            
            if submitted:
                user = check_login(username, password)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user_role'] = user['role']
                    st.session_state['user_name'] = user['name']
                    st.success(f"Welcome, {user['name']}")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Invalid ID or Password")

# --- 6. MAIN APP ---
def main_app():
    role = st.session_state['user_role']
    user_name = st.session_state['user_name']

    # --- Sidebar ---
    with st.sidebar:
        st.title("Aquench ERP")
        st.write(f"👤 **{user_name}**")
        st.caption(f"Role: {role}")
        st.write("---")

        # Menu Options
        menu_options = ["Dashboard"] # Default
        
        if role == "Admin":
            menu_options = ["Dashboard", "Order Management", "Production", "Store", "Ecommerce", "User Mgmt"]
        elif role in ["Production", "Packing"]:
            # Packing and Production share the Production module view
            menu_options = ["Dashboard", "Production"]
        elif role == "Store":
            menu_options = ["Dashboard", "Store"]
        elif role == "Ecommerce":
            menu_options = ["Dashboard", "Ecommerce"]

        selection = st.radio("Navigate", menu_options)
        
        st.write("---")
        if st.button("Logout", type="primary"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- Content ---
    if selection == "Dashboard":
        st.title("📊 Command Center")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Orders", "1,204", "+12%")
        col2.metric("Pending", "45", "-2%")
        col3.metric("Production", "12", "Normal")
        col4.metric("Returns", "3", "-1%")

    elif selection == "Order Management":
        st.title("📦 Order Management")
        st.info("Under Construction")

    elif selection == "Production":
        st.title("🏭 Production & Packing")
        
        def smart_format(num):
            try:
                f_num = float(num)
                if f_num.is_integer(): return int(f_num)
                return round(f_num, 1)
            except: return num

        # Tab Access Control
        if role == "Admin":
            tab_names = ["📌 Pending Cards", "➕ Create Task", "📅 Upcoming Table", "📜 History"]
            tabs = st.tabs(tab_names)
            t_pending, t_create, t_upcoming, t_history = tabs[0], tabs[1], tabs[2], tabs[3]
        else:
            # Production & Packing Roles see this
            tab_names = ["📌 Pending Cards", "📅 Upcoming Table"]
            tabs = st.tabs(tab_names)
            t_pending, t_upcoming = tabs[0], tabs[1]

        # 1. Create Task (Admin Only)
        if role == "Admin":
            with t_create:
                with st.form("create_task"):
                    c1, c2 = st.columns(2)
                    task_date = c1.date_input("Date")
                    item_name = c2.text_input("Item Name")
                    c3, c4 = st.columns(2)
                    target = c3.number_input("Target Qty", min_value=1.0)
                    priority = c4.selectbox("Priority", [1, 2, 3])
                    notes = st.text_area("Notes")
                    if st.form_submit_button("Assign Task"):
                        tasks_collection.insert_one({
                            "date": str(task_date),
                            "item_name": item_name,
                            "target_qty": target,
                            "ready_qty": 0,
                            "priority": priority,
                            "notes": notes,
                            "status": "Pending"
                        })
                        st.success("Task Created")
                        time.sleep(1)
                        st.rerun()

        # 2. Pending Cards
        with t_pending:
            # Sort: Priority then Date
            cursor = tasks_collection.find({"status": {"$ne": "Complete"}}).sort([("priority", 1), ("date", 1)])
            tasks = list(cursor)
            
            today = str(datetime.date.today())
            backlog = [t for t in tasks if t['date'] < today]
            today_t = [t for t in tasks if t['date'] == today]
            upcoming = [t for t in tasks if t['date'] > today]

            def show_card(task, color):
                with st.container():
                    st.markdown(f"""
                    <div style="border-left: 5px solid {color}; background: white; padding: 10px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        <div style="font-weight:bold; color:#001f3f;">{task['item_name']}</div>
                        <div style="font-size:0.85em; color:#666;">{task['date']} | P{task['priority']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    c1.metric("Target", smart_format(task['target_qty']))
                    c2.metric("Ready", smart_format(task['ready_qty']))
                    
                    with st.expander("Update"):
                        with st.form(f"upd_{task['_id']}"):
                            n_ready = st.number_input("Ready", value=float(task.get('ready_qty', 0)))
                            n_stat = st.selectbox("Status", ["Pending", "Complete"], index=0)
                            if st.form_submit_button("Save"):
                                tasks_collection.update_one({"_id": task['_id']}, {"$set": {"ready_qty": n_ready, "status": n_stat}})
                                st.rerun()
                                
            if backlog:
                st.subheader("🔴 Backlog")
                for t in backlog: show_card(t, "#FF4136")
            
            st.subheader("🟢 Today")
            for t in today_t: show_card(t, "#2ECC40")
            
            if upcoming:
                st.subheader("🔵 Upcoming")
                for t in upcoming: show_card(t, "#0074D9")

        # 3. Upcoming Table
        with t_upcoming:
            st.subheader("📅 Future Plan")
            future_tasks = list(tasks_collection.find({"date": {"$gt": today}}).sort("date", 1))
            if future_tasks:
                st.dataframe(pd.DataFrame(future_tasks)[["date", "item_name", "target_qty", "priority"]])
            else:
                st.info("No upcoming tasks")

        # 4. History (Admin Only)
        if role == "Admin":
            with t_history:
                st.subheader("History")
                st.dataframe(pd.DataFrame(list(tasks_collection.find().limit(50))))

    elif selection == "Store":
        st.title("🏪 Store Inventory")
        st.write("Inventory Logic Here")

    elif selection == "Ecommerce":
        st.title("🛒 Ecommerce Analytics")
        st.write("Analytics Here")
    
    elif selection == "User Mgmt":
        st.title("👥 User Management")
        st.dataframe(pd.DataFrame(list(users_collection.find({}, {"_id":0, "password":0}))))

# --- 7. RUN ---
if st.session_state['logged_in']:
    main_app()
else:
    login_page()
