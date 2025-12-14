import streamlit as st
import pymongo
import time
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px

# --- 1. CONFIGURATION & VISUAL STYLING ---
st.set_page_config(page_title="Aquench ERP", layout="wide", page_icon="🏭")

st.markdown("""
    <style>
        /* 1. MAIN BACKGROUND */
        [data-testid="stAppViewContainer"] {
            background-color: #F2F5F9;
        }
        
        /* 2. SIDEBAR */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            box-shadow: 2px 0 5px rgba(0,0,0,0.05);
        }
        [data-testid="stSidebar"] * {
            color: #001f3f;
            font-size: 16px;
        }
        
        /* 3. NAVIGATION */
        div[role="radiogroup"] > label > div:first-of-type { display: none; }
        div[role="radiogroup"] > label {
            background-color: transparent;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 5px;
            border: 1px solid transparent;
            transition: all 0.3s;
        }
        div[role="radiogroup"] > label:hover {
            background-color: #E8EEF1 !important;
        }
        div[role="radiogroup"] > label[data-selected="true"] {
            background-color: #FF851B !important;
            color: #FFFFFF !important;
            box-shadow: 0 2px 5px rgba(255, 133, 27, 0.3);
        }
        div[role="radiogroup"] > label[data-selected="true"] * {
            color: #FFFFFF !important;
        }

        /* 4. GENERAL CONTAINERS */
        [data-testid="stForm"] {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #E0E0E0;
        }
        [data-testid="stMetric"] {
            background-color: #FFFFFF;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid #F0F0F0;
            text-align: center;
        }

        /* 5. UNIFIED TASK CARD STYLING */
        .task-card {
            background-color: #FFFFFF;
            padding: 1.2rem;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.08);
            margin-bottom: 0.5rem; /* Reduced margin to stick to expander */
            border: 1px solid #D1D9E6;
            position: relative;
        }
        .task-header {
            font-weight: 700;
            font-size: 1.2em;
            color: #001f3f;
            margin-bottom: 4px;
            line-height: 1.3;
            word-wrap: break-word;
        }
        .task-sub {
            font-size: 0.9em;
            color: #555;
            margin-bottom: 12px;
        }
        .task-metrics {
            display: flex;
            justify-content: space-between;
            background-color: #F8F9FA;
            padding: 10px;
            border-radius: 8px;
            margin-top: 10px;
            border: 1px solid #EEE;
        }
        .metric-item {
            text-align: center;
            width: 48%;
        }
        .metric-label {
            font-size: 0.8em;
            color: #777;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 1.1em;
            font-weight: 700;
            color: #001f3f;
        }
        .badge {
            background: #F4F6F9;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.85em;
            display: inline-block;
            margin-bottom: 10px;
            font-weight: 600;
            color: #444;
            border: 1px solid #eee;
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
    """Optimized Unified Card Renderer"""
    with st.container():
        # Party Badge Logic
        party_html = ""
        if 'party_name' in task:
            party_html = f"<div class='badge'>🏢 {task.get('party_name', 'Unknown')}</div>"
        
        # Prepare Data for HTML
        target_val = smart_format(task['target_qty'])
        ready_val = smart_format(task.get('ready_qty', 0))
        
        # Extra Specs for Packing
        specs_html = ""
        if 'box_type' in task:
            specs_html = f"""
            <div style="font-size:0.85em; color:#666; margin-top:8px; padding-top:8px; border-top:1px dashed #eee;">
                📦 {task.get('box_type')} &nbsp;|&nbsp; 🏷️ {task.get('logo_status')} &nbsp;|&nbsp; ⬇️ {task.get('bottom_print')}
            </div>
            """

        # UNIFIED HTML CARD
        st.markdown(f"""
<div class="task-card" style="border-left: 6px solid {color};">
    {party_html}
    <div class="task-header">{task['item_name']}</div>
    <div class="task-sub">📅 {task['date']} &nbsp;|&nbsp; ⚡ Priority: <b>{task['priority']}</b></div>
    <div style="font-size:0.9em; color:#777; font-style:italic;">{task.get('notes', 'No notes')}</div>
    {specs_html}
    
    <div class="task-metrics">
        <div class="metric-item">
            <div class="metric-label">Target</div>
            <div class="metric-value">{target_val}</div>
        </div>
        <div style="border-right: 1px solid #DDD;"></div>
        <div class="metric-item">
            <div class="metric-label">Ready</div>
            <div class="metric-value">{ready_val}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
        
        # ACTIONS (Hidden by default to save space, but attached to card)
        with st.expander("📝 Update Status"):
            with st.form(f"upd_{task['_id']}"):
                n_ready = st.number_input("Ready Quantity", value=float(task.get('ready_qty', 0)), step=1.0)
                n_stat = st.selectbox("Status", ["Pending", "Complete"], index=0)
                
                # Mobile-friendly full width buttons
                if st.form_submit_button("💾 Save Progress", use_container_width=True):
                    collection.update_one({"_id": task['_id']}, {"$set": {"ready_qty": n_ready, "status": n_stat}})
                    st.rerun()
                
                if role_can_delete:
                    if st.form_submit_button("🗑 Delete Task", type="primary", use_container_width=True):
                        collection.delete_one({"_id": task['_id']})
                        st.rerun()

# --- 6. PAGE LOGIC ---
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
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
        tot_orders = orders_collection.count_documents({"type": "Order Received"})
        tot_pend = packing_collection.count_documents({"status": "Pending"})
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Orders", tot_orders)
        c2.metric("Packing Jobs", tot_pend)
        c3.metric("Production Queue", tasks_collection.count_documents({"status": "Pending"}))
        c4.metric("Active Users", "5", "+0")

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
                
                if st.form_submit_button("Save Transaction", use_container_width=True):
                    if o_party and o_item:
                        orders_collection.insert_one({
                            "date": str(o_date), "type": o_type, "party": o_party,
                            "item": o_item, "qty": o_qty, "timestamp": time.time()
                        })
                        st.success("Saved!")
                    else: st.error("Party and Item Name are required.")
        
        with t2:
            st.subheader("Pending Liabilities")
            data = list(orders_collection.find())
            if data:
                df = pd.DataFrame(data)
                df['net_qty'] = df.apply(lambda x: x['qty'] if x['type'] == 'Order Received' else -x['qty'], axis=1)
                pivot = df.pivot_table(index="item", columns="party", values="net_qty", aggfunc="sum", fill_value=0)
                pivot = pivot.loc[(pivot != 0).any(axis=1)]
                st.dataframe(pivot, use_container_width=True)
                
                st.write("#### ⚠️ High Pending Items")
                summary = df.groupby(['item'])['net_qty'].sum().sort_values(ascending=False).head(5)
                st.dataframe(summary)
            else: st.info("No transaction data.")

    # --- TAB: PRODUCTION ---
    elif sel == "Production":
        st.title("🏭 Production Floor")
        if role == "Admin":
            t_pend, t_new, t_table = st.tabs(["Cards", "Create", "Table"])
        else:
            t_pend, t_table = st.tabs(["Cards", "Table"])
            
        with t_pend:
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
                st.subheader("New Production Task")
                with st.form("new_prod"):
                    d = st.date_input("Date")
                    i = st.text_input("Item")
                    q = st.number_input("Target", min_value=1.0)
                    p = st.selectbox("Priority", [1,2,3])
                    if st.form_submit_button("Assign", use_container_width=True):
                        tasks_collection.insert_one({"date":str(d), "item_name":i, "target_qty":q, "ready_qty":0, "priority":p, "status":"Pending"})
                        st.success("Assigned"); st.rerun()
        
        with t_table:
            st.dataframe(pd.DataFrame(list(tasks_collection.find({},{"_id":0}).limit(50))))

    # --- TAB: PACKING ---
    elif sel == "Packing":
        st.title("📦 Packing Department")
        if role == "Admin":
            tabs = st.tabs(["📌 Packing Cards", "➕ Create Job", "📅 Table", "📜 History"])
            t_cards, t_create, t_table, t_hist = tabs[0], tabs[1], tabs[2], tabs[3]
        else:
            tabs = st.tabs(["📌 Packing Cards", "📅 Table"])
            t_cards, t_table = tabs[0], tabs[1]

        if role == "Admin":
            with t_create:
                st.subheader("Assign Packing Job")
                with st.form("pack_create"):
                    c1, c2 = st.columns(2)
                    pd_date = c1.date_input("Packing Date")
                    pd_party = c2.text_input("Party Name")
                    c3, c4 = st.columns(2)
                    pd_item = c3.text_input("Item Name")
                    pd_qty = c4.number_input("Target Qty", min_value=1.0)
                    st.markdown("**Specs:**")
                    r1, r2, r3, r4 = st.columns(4)
                    pd_prio = r1.selectbox("Priority", [1,2,3])
                    pd_box = r2.selectbox("Box Type", ["Master", "Inner", "Custom", "Loose"])
                    pd_logo = r3.text_input("Logo Status", "Standard")
                    pd_bot = r4.text_input("Bottom Print", "N/A")
                    if st.form_submit_button("🚀 Assign Packing", use_container_width=True):
                        packing_collection.insert_one({
                            "date": str(pd_date), "party_name": pd_party, "item_name": pd_item,
                            "target_qty": pd_qty, "ready_qty": 0, "priority": pd_prio,
                            "box_type": pd_box, "logo_status": pd_logo, "bottom_print": pd_bot,
                            "status": "Pending"
                        })
                        st.success("Created!"); time.sleep(1); st.rerun()

        with t_cards:
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

        with t_table:
            st.dataframe(pd.DataFrame(list(packing_collection.find({"date": {"$gt": today_str}}, {"_id":0}).sort("date", 1))))

        if role == "Admin":
            with t_hist:
                st.dataframe(pd.DataFrame(list(packing_collection.find({}, {"_id":0}).limit(100))))

    # --- TAB: STORE ---
    elif sel == "Store":
        st.title("🏪 Store & Inventory")
        t1, t2, t3 = st.tabs(["📊 Live Stock", "🧠 Planning", "📥 Transaction"])
        
        with t1:
            search = st.text_input("🔍 Search Inventory", placeholder="Item Name...")
            all_trans = list(store_collection.find())
            if all_trans:
                sdf = pd.DataFrame(all_trans)
                if search: sdf = sdf[sdf['item'].str.contains(search, case=False, na=False)]
                if not sdf.empty:
                    sdf['net_qty'] = sdf.apply(lambda x: x['qty'] if x['type'] == 'Inward' else -x['qty'], axis=1)
                    stock = sdf.groupby('item')['net_qty'].sum().reset_index()
                    st.dataframe(stock.rename(columns={'net_qty': 'Stock'}), use_container_width=True)
                else: st.info("No items found.")
            else: st.info("Empty Stock.")

        with t2:
            st.subheader("📦 Material Forecast")
            today = datetime.date.today()
            start, end = str(today - timedelta(days=7)), str(today + timedelta(days=5))
            req_list = list(packing_collection.find({"date": {"$gte": start, "$lte": end}}))
            if req_list:
                rdf = pd.DataFrame(req_list)
                st.table(rdf.groupby('box_type')['target_qty'].sum().reset_index())
                st.dataframe(rdf[['date', 'party_name', 'item_name', 'box_type']])
            else: st.success("No upcoming packing jobs.")

        with t3:
            st.subheader("New Stock Entry")
            with st.form("store_entry"):
                c1, c2 = st.columns(2)
                s_date = c1.date_input("Date")
                s_type = c2.selectbox("Type", ["Inward", "Outward"])
                s_item = st.text_input("Item Name")
                s_qty = st.number_input("Qty", step=0.1)
                s_note = st.text_input("Note")
                if st.form_submit_button("Update Stock", use_container_width=True):
                    store_collection.insert_one({"date": str(s_date), "type": s_type, "item": s_item, "qty": s_qty, "notes": s_note})
                    st.success("Updated"); time.sleep(1); st.rerun()

    # --- TAB: ECOMMERCE ---
    elif sel == "Ecommerce":
        st.title("🛒 Ecommerce Analytics")
        t1, t2 = st.tabs(["📈 Performance", "📝 Daily Log"])
        
        with t1:
            st.subheader("Sales Dashboard")
            e_data = list(ecom_collection.find())
            if e_data:
                edf = pd.DataFrame(e_data)
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Orders", int(edf['orders'].sum()))
                m2.metric("Dispatches", int(edf['dispatches'].sum()))
                m3.metric("Returns", int(edf['returns'].sum()))
                
                c1, c2 = st.columns([2, 1])
                with c1: st.plotly_chart(px.line(edf, x="date", y="orders", color="channel", title="Order Trend"), use_container_width=True)
                with c2: st.plotly_chart(px.pie(edf, values="orders", names="channel", title="Share"), use_container_width=True)
            else: st.info("No Data.")

        with t2:
            st.subheader("Log Sales Data")
            with st.form("ecom_entry"):
                c1, c2 = st.columns(2)
                e_date = c1.date_input("Date")
                e_chan = c2.selectbox("Channel", ["Amazon", "Flipkart", "Website", "Meesho"])
                c3, c4, c5 = st.columns(3)
                e_ord = c3.number_input("Orders", min_value=0)
                e_dis = c4.number_input("Dispatches", min_value=0)
                e_ret = c5.number_input("Returns", min_value=0)
                if st.form_submit_button("Save Log", use_container_width=True):
                    ecom_collection.insert_one({"date": str(e_date), "channel": e_chan, "orders": e_ord, "dispatches": e_dis, "returns": e_ret})
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
