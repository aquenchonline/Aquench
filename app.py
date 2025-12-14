import streamlit as st
import pymongo
import pandas as pd

# --- 1. CONFIGURATION & CSS (AdminUX) ---
st.set_page_config(page_title="ERP System", layout="wide")

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
    # USES THE CONNECTION STRING YOU FIXED IN SECRETS.TOML
    return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])

try:
    client = init_connection()
    db = client.my_erp_db  # Change this to your preferred DB name
    st.sidebar.success("🟢 Database Connected")
except Exception as e:
    st.sidebar.error(f"🔴 DB Connection Failed: {e}")

# --- 3. MAIN APP LOGIC ---

# sidebar Logic
with st.sidebar:
    st.header("ERP System")
    
    # --- DEBUG: ROLE SWITCHER (For Testing Only) ---
    st.info("🛠 Dev Mode: Select Role")
    current_role = st.selectbox("View App As:", ["Admin", "Production", "Store", "Ecommerce"])
    st.write("---")

    # Define Menu Options based on the role selected above
    if current_role == "Admin":
        menu_options = ["Dashboard", "Order Management", "Production", "Store", "Ecommerce", "User Mgmt"]
    elif current_role == "Production":
        menu_options = ["Dashboard", "Production"]
    elif current_role == "Store":
        menu_options = ["Dashboard", "Store"]
    elif current_role == "Ecommerce":
        menu_options = ["Dashboard", "Ecommerce"]
    
    selection = st.radio("Navigate", menu_options)

# --- Page Content Router ---

if selection == "Dashboard":
    st.title("📊 Command Center")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders", "1,204", "+12%")
    col2.metric("Pending Dispatch", "45", "-2%")
    col3.metric("Production Queue", "12", "Normal")
    col4.metric("Returns", "3", "-1%")
    
    st.subheader("Global Overview")
    st.write(f"You are viewing data as: **{current_role}**")

elif selection == "Order Management":
    st.title("📦 Order Management")
    st.info("Input: Order Received / Dispatch -> Output: Pending Balance")
    
    # Placeholder for Matrix View
    st.write("### Pending Orders Matrix")
    # Dummy Data for visualization
    df = pd.DataFrame({
        "Party Name": ["Party A", "Party B", "Party A"],
        "Item": ["Widget X", "Widget Y", "Widget X"],
        "Ordered": [100, 50, 200],
        "Dispatched": [80, 50, 0],
        "Balance": [20, 0, 200]
    })
    st.dataframe(df, use_container_width=True)

elif selection == "Production":
    st.title("🏭 Production & Packing")
    
    if current_role == "Admin":
        st.success("Admin Controls Visible: [Create Task] [Delete Task]")
        tab1, tab2, tab3 = st.tabs(["🔴 Backlog", "🟢 Today", "🔵 Upcoming"])
        with tab1:
            st.write("Tasks delayed from yesterday...")
    else:
        st.info("Worker View: Update Status Only")
        st.write("List of assigned tasks...")

elif selection == "Store":
    st.title("🏪 Store Inventory")
    st.write("Live Stock = Inward - Outward")
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("📥 Record Inward Entry")
    with col2:
        st.button("📤 Record Outward Entry")

elif selection == "Ecommerce":
    st.title("🛒 Ecommerce Analytics")
    st.write("Compare Today vs Last 7 Days")

elif selection == "User Mgmt":
    st.title("👥 User Management")
    st.write("Admin panel to add/remove users.")
