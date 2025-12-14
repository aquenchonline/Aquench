import streamlit as st
import pymongo
import time
import pandas as pd
import datetime

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

db = client.my_erp_db  # Your Database Name
users_collection = db.users
tasks_collection = db.production_tasks

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
        st.info(f"You are logged in as **{role}**")

    elif selection == "Order Management":
        st.title("📦 Order Management")
        st.info("Input: Order Received / Dispatch -> Output: Pending Balance")
        
        # Placeholder for Matrix View
        st.write("### Pending Orders Matrix (Demo)")
        df = pd.DataFrame({
            "Party Name": ["Party A", "Party B", "Party A"],
            "Item": ["Widget X", "Widget Y", "Widget X"],
            "Ordered": [100, 50, 200],
            "Dispatched": [80, 50, 0],
            "Balance": [20, 0, 200]
        })
        st.dataframe(df, use_container_width=True)

    elif selection == "Production":
        st.title("🏭 Production Management")
        
        # --- Helper Functions ---
        def smart_format(num):
            """Converts 100.0 -> 100, 10.5 -> 10.5"""
            try:
                f_num = float(num)
                if f_num.is_integer():
                    return int(f_num)
                return round(f_num, 1)
            except:
                return num

        # --- Tab Logic based on Role ---
        if role == "Admin":
            tab_names = ["📌 Pending Cards", "➕ Create Task", "📅 Upcoming Table", "📜 All Tasks (History)"]
            tabs = st.tabs(tab_names)
            t_pending, t_create, t_upcoming, t_history = tabs[0], tabs[1], tabs[2], tabs[3]
        else:
            # Production Incharge sees restricted view
            tab_names = ["📌 Pending Cards", "📅 Upcoming Table"]
            tabs = st.tabs(tab_names)
            t_pending, t_upcoming = tabs[0], tabs[1]

        # --- TAB: CREATE TASK (Admin Only) ---
        if role == "Admin":
            with t_create:
                st.subheader("Assign New Job")
                with st.form("create_task_form"):
                    c1, c2 = st.columns(2)
                    task_date = c1.date_input("Production Date")
                    item_name = c2.text_input("Item / Product Name")
                    
                    c3, c4 = st.columns(2)
                    target_qty = c3.number_input("Target Qty", min_value=1.0, step=1.0)
                    priority = c4.selectbox("Priority", [1, 2, 3], help="1 = High, 3 = Low")
                    
                    notes = st.text_area("Special Instructions")
                    
                    submitted = st.form_submit_button("🚀 Assign Task", use_container_width=True)
                    
                    if submitted:
                        new_task = {
                            "date": str(task_date), # Store as string YYYY-MM-DD
                            "item_name": item_name,
                            "target_qty": target_qty,
                            "ready_qty": 0,
                            "priority": priority,
                            "notes": notes,
                            "status": "Pending",
                            "created_at": time.time()
                        }
                        tasks_collection.insert_one(new_task)
                        st.success(f"Task for {item_name} assigned!")
                        time.sleep(1)
                        st.rerun()

        # --- TAB: PENDING CARDS (The Main Dashboard) ---
        with t_pending:
            st.subheader("Live Job Cards")
            
            # Fetch only incomplete tasks
            # Sort: Priority (1=High), then Date (Oldest)
            pending_cursor = tasks_collection.find({"status": {"$ne": "Complete"}}).sort([("priority", 1), ("date", 1)])
            all_pending = list(pending_cursor)
            
            # Categorize into Buckets
            today_str = str(datetime.date.today())
            
            backlog = [t for t in all_pending if t['date'] < today_str]
            today_tasks = [t for t in all_pending if t['date'] == today_str]
            upcoming = [t for t in all_pending if t['date'] > today_str]
            
            # Render Function for Cards
            def render_task_card(task, color_bar):
                # Card Container
                with st.container():
                    st.markdown(f"""
                    <div style="
                        border-left: 5px solid {color_bar}; 
                        background-color: white; 
                        padding: 15px; 
                        border-radius: 5px; 
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                        margin-bottom: 10px;">
                        <h4 style="margin:0; color:#001f3f;">{task['item_name']}</h4>
                        <p style="margin:0; font-size: 0.9em; color: #666;">
                            📅 {task['date']} | ⚡ Priority: {task['priority']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Metrics Row
                    c1, c2, c3 = st.columns([1, 1, 2])
                    c1.metric("Target", smart_format(task['target_qty']))
                    c2.metric("Ready", smart_format(task['ready_qty']))
                    
                    # Update Expander
                    with st.expander("Update Progress"):
                        with st.form(f"update_{task['_id']}"):
                            new_ready = st.number_input("Ready Qty", value=float(task['ready_qty']), key=f"qty_{task['_id']}")
                            new_status = st.selectbox("Status", ["Pending", "In Progress", "Hold", "Complete"], index=0, key=f"stat_{task['_id']}")
                            
                            btn_col1, btn_col2 = st.columns(2)
                            update_click = btn_col1.form_submit_button("💾 Save", use_container_width=True)
                            
                            # Delete Button (Admin Only)
                            delete_click = False
                            if role == "Admin":
                                delete_click = btn_col2.form_submit_button("🗑 Delete", type="primary", use_container_width=True)
                            
                            if update_click:
                                tasks_collection.update_one(
                                    {"_id": task["_id"]}, 
                                    {"$set": {"ready_qty": new_ready, "status": new_status}}
                                )
                                st.success("Updated!")
                                time.sleep(0.5)
                                st.rerun()
                                
                            if delete_click:
                                tasks_collection.delete_one({"_id": task["_id"]})
                                st.warning("Deleted!")
                                time.sleep(0.5)
                                st.rerun()

            # 🔴 Backlog Section
            if backlog:
                st.markdown("### 🔴 Backlog (Overdue)")
                for task in backlog:
                    render_task_card(task, "#FF4136") # Red
            
            # 🟢 Today Section
            st.markdown("### 🟢 Today's Plan")
            if not today_tasks:
                st.info("No tasks scheduled for today.")
            for task in today_tasks:
                render_task_card(task, "#2ECC40") # Green
            
            # 🔵 Upcoming Section
            if upcoming:
                st.markdown("### 🔵 Upcoming Pending")
                for task in upcoming:
                    render_task_card(task, "#0074D9") # Blue

        # --- TAB: UPCOMING TABLE ---
        with t_upcoming:
            st.subheader("📅 Future Planning")
            future_cursor = tasks_collection.find({"date": {"$gt": today_str}}).sort("date", 1)
            future_data = list(future_cursor)
            
            if future_data:
                df_future = pd.DataFrame(future_data)
                display_cols = ["date", "item_name", "target_qty", "priority", "notes"]
                st.dataframe(df_future[display_cols], use_container_width=True)
            else:
                st.info("No upcoming tasks.")

        # --- TAB: HISTORY (Admin Only) ---
        if role == "Admin":
            with t_history:
                st.subheader("📜 All Tasks History")
                
                search_query = st.text_input("🔍 Search by Item Name", "")
                
                query = {}
                if search_query:
                    query["item_name"] = {"$regex": search_query, "$options": "i"}
                
                # Pagination
                page_size = 10
                total_docs = tasks_collection.count_documents(query)
                total_pages = max(1, (total_docs + page_size - 1) // page_size)
                
                page_num = st.number_input("Page", min_value=1, max_value=total_pages, step=1)
                skip_count = (page_num - 1) * page_size
                
                history_cursor = tasks_collection.find(query).sort("date", -1).skip(skip_count).limit(page_size)
                history_data = list(history_cursor)
                
                if history_data:
                    df_hist = pd.DataFrame(history_data)
                    df_hist['_id'] = df_hist['_id'].astype(str)
                    st.dataframe(
                        df_hist[['date', 'item_name', 'target_qty', 'ready_qty', 'status']], 
                        use_container_width=True
                    )
                else:
                    st.info("No records found.")

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
