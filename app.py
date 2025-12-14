import streamlit as st
import pymongo
import time
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px

# --- 1. CONFIGURATION & CSS (AdminUX) ---
st.set_page_config(page_title="Aquench ERP", layout="wide", page_icon="🏭")

# Custom CSS for UI Polish
st.markdown("""
    <style>
        [data-testid="stSidebar"] { background-color: #FFFFFF; }
        [data-testid="stSidebar"] * { color: #001f3f; font-size: 16px; }
        div[role="radiogroup"] > label > div:first-of-type { display: none; }
        div[role="radiogroup"] > label {
            background-color: #F0F2F6; padding: 10px; border-radius: 8px;
            margin-bottom: 5px; border: 1px solid #ddd; transition: all 0.3s;
        }
        div[role="radiogroup"] > label:hover {
            background-color: #001f3f !important; color: #FFFFFF !important;
        }
        div[role="radiogroup"] > label[data-selected="true"] {
            background-color: #FF851B !important; color: #FFFFFF !important;
            border-left: 6px solid #001f3f;
        }
        div[role="radiogroup"] > label[data-selected="true"] * { color: #FFFFFF !important; }
        
        /* Card Styling */
        .task-card {
            background-color: white; padding: 15px; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 12px;
        }
        .metric-box {
            text-align: center; border: 1px solid #eee; padding: 10px; border-radius: 5px;
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
if not client: st.stop()

db = client.my_erp_db
users_collection = db.users
tasks_collection = db.production_tasks
orders_collection = db.orders
packing_collection = db.packing_tasks
store_collection = db.store_transactions
ecom_collection = db.ecommerce_logs

# --- 3. AUTO-SETUP USERS ---
def setup_initial_users():
    required_users = [
        {"username": "production", "password": "Amavik@80", "role": "Production", "name": "Production Incharge"},
        {"username": "packing", "password": "Amavik@97", "role": "Packing", "name": "Packing Incharge"},
        {"username": "store", "password": "Amavik@17", "role": "Store", "name": "Store Manager"},
        {"username": "ecommerce", "password": "Amavik@12", "role": "Ecommerce", "name": "Ecom Manager"},
        {"username": "amar", "password": "Aquench@1933", "role": "Admin", "name": "Amar (Admin)"}
    ]
    for user in required_users:
        if not users_collection.find_one({"username": user["username"]}):
            users_collection.insert_one(user)

setup_initial_users()

# --- 4. AUTH & SESSION ---
def check_login(username, password):
    if not username or not password: return None
    user = users_collection.find_one({"username": username.lower()})
    if user and user['password'] == password: return user
    return None

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['user_name'] = None

# --- 5. HELPER FUNCTIONS ---
def smart_format(num):
    try:
        f_num = float(num)
        if f_num.is_integer(): return int(f_num)
        return round(f_num, 1)
    except: return num

def render_task_card(task, color, collection, role_can_delete=False):
    """Generic Card Renderer for Production and Packing"""
    with st.container():
        # Packing Logic adds Party Name highlight
        party_html = f"<div style='background:#eee; padding:2px 6px; border-radius:4px; font-size:0.8em; display:inline-block; margin-bottom:5px;'>🏢 {task.get('party_name', 'Unknown')}</div>" if 'party_name' in task else ""
        
        st.markdown(f"""
        <div class="task-card" style="border-left: 5px solid {color};">
            {party_html}
            <div style="font-weight:bold; font-size:1.1em; color:#001f3f;">{task['item_name']}</div>
            <div style="font-size:0.85em; color:#666;">📅 {task['date']} | ⚡ P{task['priority']}</div>
            <div style="font-size:0.8em; color:#888; margin-top:5px;">{task.get('notes', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Packing Specific Details
        if 'box_type' in task:
            st.markdown(f"**📦 {task.get('box_type')}** | 🏷️ {task.get('logo_status')} | ⬇️ {task.get('bottom_print')}")

        c1, c2 = st.columns(2)
        c1.metric("Target", smart_format(task['target_qty']))
        c2.metric("Ready", smart_format(task['ready_qty']))
        
        with st.expander("Update / Action"):
            with st.form(f"upd_{task['_id']}"):
                n_ready = st.number_input("Ready Qty", value=float(task.get('ready_qty', 0)))
                n_stat = st.selectbox("Status", ["Pending", "Complete"], index=0)
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.form_submit_button("💾 Save"):
                    collection.update_one({"_id": task['_id']}, {"$set": {"ready_qty": n_ready, "status": n_stat}})
                    st.rerun()
                
                if role_can_delete:
                    if c_btn2.form_submit_button("🗑 Delete"):
                        collection.delete_one({"_id": task['_id']})
                        st.rerun()

# --- 6. PAGE LOGIC ---
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Aquench ERP")
        st.markdown("##### System Access")
        with st.form("login"):
            u = st.text_input("User ID")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                user = check_login(u, p)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user_role'] = user['role']
                    st.session_state['user_name'] = user['name']
                    st.success("Login Success")
                    time.sleep(0.5)
                    st.rerun()
                else: st.error("Invalid Credentials")

def main_app():
    role = st.session_state['user_role']
    user_name = st.session_state['user_name']

    with st.sidebar:
        st.title("🏭 Aquench ERP")
        st.write(f"**{user_name}** ({role})")
        st.write("---")
        
        # Menu Permissions
        opts = ["Dashboard"]
        if role == "Admin": opts += ["Order Mgmt", "Production", "Packing", "Store", "Ecommerce", "User Mgmt"]
        elif role == "Production": opts = ["Dashboard", "Production"]
        elif role == "Packing": opts = ["Dashboard", "Packing"]
        elif role == "Store": opts = ["Dashboard", "Store"]
        elif role == "Ecommerce": opts = ["Dashboard", "Order Mgmt", "Ecommerce"]
        
        sel = st.radio("Navigate", opts)
        
        st.write("---")
        if st.button("Logout", type="primary"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- TAB: DASHBOARD ---
    if sel == "Dashboard":
        st.title("📊 Command Center")
        # Quick Stats from DB
        tot_orders = orders_collection.count_documents({"type": "Order Received"})
        tot_pend = packing_collection.count_documents({"status": "Pending"})
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Orders Logged", tot_orders)
        c2.metric("Packing Pending", tot_pend)
        c3.metric("Production Queue", tasks_collection.count_documents({"status": "Pending"}))
        c4.metric("System Status", "Online", "🟢")

    # --- TAB: ORDER MANAGEMENT ---
    elif sel == "Order Mgmt":
        st.title("📑 Order Management")
        
        t1, t2 = st.tabs(["📝 Data Entry", "📉 Pending Matrix"])
        
        with t1:
            st.subheader("Log Transaction")
            with st.form("order_entry"):
                c1, c2, c3 = st.columns(3)
                o_date = c1.date_input("Date")
                o_type = c2.selectbox("Type", ["Order Received", "Dispatch"])
                o_party = c3.text_input("Party Name")
                
                c4, c5 = st.columns(2)
                o_item = c4.text_input("Item Name")
                o_qty = c5.number_input("Quantity", min_value=1.0)
                
                if st.form_submit_button("Save Transaction"):
                    if o_party and o_item:
                        orders_collection.insert_one({
                            "date": str(o_date), "type": o_type, "party": o_party,
                            "item": o_item, "qty": o_qty, "timestamp": time.time()
                        })
                        st.success("Saved!")
                    else: st.error("Party and Item Name are required.")
        
        with t2:
            st.subheader("Pending Liabilities (Received - Dispatched)")
            # Fetch All Data
            data = list(orders_collection.find())
            if data:
                df = pd.DataFrame(data)
                # Calculate Net Qty (Received = +, Dispatch = -)
                df['net_qty'] = df.apply(lambda x: x['qty'] if x['type'] == 'Order Received' else -x['qty'], axis=1)
                
                # Pivot Table
                pivot = df.pivot_table(index="item", columns="party", values="net_qty", aggfunc="sum", fill_value=0)
                
                # Filter out zero balances for cleaner view
                pivot = pivot.loc[(pivot != 0).any(axis=1)]
                
                st.dataframe(pivot.style.background_gradient(cmap="Reds", axis=None).format("{:.1f}"), use_container_width=True)
                
                st.write("#### ⚠️ High Pending Items")
                summary = df.groupby(['item'])['net_qty'].sum().sort_values(ascending=False).head(5)
                st.dataframe(summary)
            else:
                st.info("No transaction data found.")

    # --- TAB: PRODUCTION ---
    elif sel == "Production":
        st.title("🏭 Production Floor")
        # (Reusing logic from previous turn, simplified for brevity)
        if role == "Admin":
            t_pend, t_new, t_table = st.tabs(["Cards", "Create", "Table"])
        else:
            t_pend, t_table = st.tabs(["Cards", "Table"])
            
        with t_pend:
            # Logic: Priority -> Date
            tasks = list(tasks_collection.find({"status": {"$ne": "Complete"}}).sort([("priority", 1), ("date", 1)]))
            today = str(datetime.date.today())
            
            backlog = [t for t in tasks if t['date'] < today]
            current = [t for t in tasks if t['date'] == today]
            future = [t for t in tasks if t['date'] > today]
            
            if backlog: 
                st.subheader("🔴 Backlog"); 
                for t in backlog: render_task_card(t, "#FF4136", tasks_collection, role=="Admin")
            st.subheader("🟢 Today"); 
            for t in current: render_task_card(t, "#2ECC40", tasks_collection, role=="Admin")
            if future: 
                st.subheader("🔵 Upcoming"); 
                for t in future: render_task_card(t, "#0074D9", tasks_collection, role=="Admin")

        if role == "Admin":
            with t_new:
                with st.form("new_prod"):
                    d = st.date_input("Date")
                    i = st.text_input("Item")
                    q = st.number_input("Target", min_value=1.0)
                    p = st.selectbox("Priority", [1,2,3])
                    if st.form_submit_button("Assign"):
                        tasks_collection.insert_one({"date":str(d), "item_name":i, "target_qty":q, "ready_qty":0, "priority":p, "status":"Pending"})
                        st.success("Assigned"); st.rerun()
        
        with t_table:
            st.dataframe(pd.DataFrame(list(tasks_collection.find({},{"_id":0}).limit(50))))

    # --- TAB: PACKING ---
    elif sel == "Packing":
        st.title("📦 Packing Department")
        
        # Tabs based on Role
        if role == "Admin":
            tabs = st.tabs(["📌 Packing Cards", "➕ Create Job", "📅 Table", "📜 History"])
            t_cards, t_create, t_table, t_hist = tabs[0], tabs[1], tabs[2], tabs[3]
        else:
            tabs = st.tabs(["📌 Packing Cards", "📅 Table"])
            t_cards, t_table = tabs[0], tabs[1]

        # 1. CREATE JOB (Admin Only)
        if role == "Admin":
            with t_create:
                st.subheader("Assign Packing Job")
                with st.form("pack_create"):
                    c1, c2 = st.columns(2)
                    pd_date = c1.date_input("Packing Date")
                    pd_party = c2.text_input("Party Name (Client)")
                    
                    c3, c4 = st.columns(2)
                    pd_item = c3.text_input("Item Name")
                    pd_qty = c4.number_input("Target Qty", min_value=1.0)
                    
                    st.markdown("**Specs:**")
                    r1, r2, r3, r4 = st.columns(4)
                    pd_prio = r1.selectbox("Priority", [1,2,3])
                    pd_box = r2.selectbox("Box Type", ["Master", "Inner", "Custom", "Loose"])
                    pd_logo = r3.text_input("Logo Status", "Standard")
                    pd_bot = r4.text_input("Bottom Print", "N/A")
                    
                    if st.form_submit_button("🚀 Assign Packing"):
                        packing_collection.insert_one({
                            "date": str(pd_date), "party_name": pd_party, "item_name": pd_item,
                            "target_qty": pd_qty, "ready_qty": 0, "priority": pd_prio,
                            "box_type": pd_box, "logo_status": pd_logo, "bottom_print": pd_bot,
                            "status": "Pending"
                        })
                        st.success("Packing Job Created!"); time.sleep(1); st.rerun()

        # 2. CARDS (Logic: Priority -> Date)
        with t_cards:
            # Fetch Incomplete
            pack_cursor = packing_collection.find({"status": {"$ne": "Complete"}}).sort([("priority", 1), ("date", 1)])
            all_pack = list(pack_cursor)
            
            today_str = str(datetime.date.today())
            p_backlog = [t for t in all_pack if t['date'] < today_str]
            p_today = [t for t in all_pack if t['date'] == today_str]
            p_upcoming = [t for t in all_pack if t['date'] > today_str]
            
            if p_backlog:
                st.subheader("🔴 Backlog"); 
                for t in p_backlog: render_task_card(t, "#FF4136", packing_collection, role=="Admin")
            
            st.subheader("🟢 Today"); 
            for t in p_today: render_task_card(t, "#2ECC40", packing_collection, role=="Admin")
            
            if p_upcoming:
                st.subheader("🔵 Upcoming"); 
                for t in p_upcoming: render_task_card(t, "#0074D9", packing_collection, role=="Admin")

        # 3. TABLE
        with t_table:
            st.dataframe(pd.DataFrame(list(packing_collection.find({"date": {"$gt": today_str}}, {"_id":0}).sort("date", 1))))

        # 4. HISTORY
        if role == "Admin":
            with t_hist:
                st.dataframe(pd.DataFrame(list(packing_collection.find({}, {"_id":0}).limit(100))))

    # --- TAB: STORE ---
    elif sel == "Store":
        st.title("🏪 Store & Inventory")
        
        t1, t2, t3 = st.tabs(["📊 Live Stock", "🧠 Planning (Predictive)", "📥 Record Transaction"])
        
        # 1. LIVE STOCK
        with t1:
            search = st.text_input("🔍 Search Inventory", placeholder="Type 'Box', 'Tape'...")
            all_trans = list(store_collection.find())
            
            if all_trans:
                sdf = pd.DataFrame(all_trans)
                # Apply Search
                if search:
                    sdf = sdf[sdf['item'].str.contains(search, case=False, na=False)]
                
                if not sdf.empty:
                    # Calculate Stock: Inward (+), Outward (-)
                    sdf['net_qty'] = sdf.apply(lambda x: x['qty'] if x['type'] == 'Inward' else -x['qty'], axis=1)
                    stock = sdf.groupby('item')['net_qty'].sum().reset_index()
                    stock.rename(columns={'net_qty': 'Current Stock'}, inplace=True)
                    
                    st.dataframe(stock.style.format({"Current Stock": "{:.1f}"}), use_container_width=True)
                else:
                    st.info("No matching items.")
            else:
                st.info("No stock data.")

        # 2. PLANNING (Predictive)
        with t2:
            st.subheader("📦 Material Requirement Forecast")
            st.info("Based on Packing Jobs: (Last 7 Days to Next 5 Days)")
            
            today = datetime.date.today()
            start = str(today - timedelta(days=7))
            end = str(today + timedelta(days=5))
            
            # Query Packing Tasks in Window
            req_cursor = packing_collection.find({"date": {"$gte": start, "$lte": end}})
            req_list = list(req_cursor)
            
            if req_list:
                rdf = pd.DataFrame(req_list)
                # Group by Box Type or Item to see what is needed
                summary = rdf.groupby('box_type')['target_qty'].sum().reset_index()
                st.markdown("#### Box Types Required")
                st.table(summary)
                
                st.markdown("#### Detailed Item List")
                st.dataframe(rdf[['date', 'party_name', 'item_name', 'box_type', 'target_qty']])
            else:
                st.success("No upcoming packing jobs found in this window.")

        # 3. RECORD TRANSACTION
        with t3:
            with st.form("store_entry"):
                c1, c2 = st.columns(2)
                s_date = c1.date_input("Date")
                s_type = c2.selectbox("Type", ["Inward", "Outward"])
                s_item = st.text_input("Item Name (e.g., 5 Ply Box)")
                s_qty = st.number_input("Quantity", step=0.1)
                s_note = st.text_input("Note / PO Number")
                
                if st.form_submit_button("Update Stock"):
                    store_collection.insert_one({
                        "date": str(s_date), "type": s_type, "item": s_item,
                        "qty": s_qty, "notes": s_note
                    })
                    st.success("Stock Updated"); time.sleep(1); st.rerun()

    # --- TAB: ECOMMERCE ---
    elif sel == "Ecommerce":
        st.title("🛒 Ecommerce Analytics")
        
        t1, t2 = st.tabs(["📈 Performance", "📝 Daily Log"])
        
        with t1:
            st.subheader("Sales Dashboard")
            period = st.selectbox("Compare With", ["Last 7 Days", "Yesterday"])
            
            # (Simplified Logic for Demo - In real app, date parsing is stricter)
            # Fetch all logs
            e_data = list(ecom_collection.find())
            if e_data:
                edf = pd.DataFrame(e_data)
                
                # Top Metrics
                total_orders = edf['orders'].sum()
                total_dispatch = edf['dispatches'].sum()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Orders", int(total_orders), "+5%") # Dummy delta for visual
                m2.metric("Dispatches", int(total_dispatch), "+2%")
                m3.metric("Returns", int(edf['returns'].sum()), "-1%")
                
                # Charts
                col_chart1, col_chart2 = st.columns([2, 1])
                
                with col_chart1:
                    # Spline Chart
                    fig = px.line(edf, x="date", y="orders", color="channel", title="Daily Order Trend", markers=True, line_shape="spline")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_chart2:
                    # Donut Chart
                    fig2 = px.pie(edf, values="orders", names="channel", title="Channel Share", hole=0.4)
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No Ecommerce Data Logged Yet.")

        with t2:
            st.subheader("Log Daily Stats")
            with st.form("ecom_entry"):
                c1, c2 = st.columns(2)
                e_date = c1.date_input("Date")
                e_chan = c2.selectbox("Channel", ["Amazon", "Flipkart", "Website", "Meesho"])
                
                c3, c4, c5 = st.columns(3)
                e_ord = c3.number_input("Orders", min_value=0)
                e_dis = c4.number_input("Dispatches", min_value=0)
                e_ret = c5.number_input("Returns", min_value=0)
                
                if st.form_submit_button("Save Log"):
                    ecom_collection.insert_one({
                        "date": str(e_date), "channel": e_chan,
                        "orders": e_ord, "dispatches": e_dis, "returns": e_ret
                    })
                    st.success("Logged!"); st.rerun()

    # --- TAB: USER MGMT ---
    elif sel == "User Mgmt":
        st.title("👥 User Management")
        st.dataframe(pd.DataFrame(list(users_collection.find({}, {"_id":0, "password":0}))))

# --- 7. RUN ---
if st.session_state['logged_in']:
    main_app()
else:
    login_page()
