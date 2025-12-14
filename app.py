import streamlit as st
import pymongo

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])

client = init_connection()

# Create a database named 'test_db' and a collection named 'test_collection'
# MongoDB creates these automatically when you first save data to them.
db = client.test_db
collection = db.test_collection

st.title("MongoDB Connection Test")

# Test Button
if st.button("Click to Check Connection"):
    try:
        # Try to insert a dummy document
        collection.insert_one({"message": "Hello MongoDB!", "status": "Success"})
        st.success("Connected successfully! Data inserted.")
        
        # Verify by reading it back
        last_item = collection.find_one(sort=[('_id', -1)]) # Get the last item
        st.write("Read from DB:", last_item['message'])
        
    except Exception as e:
        st.error(f"Connection failed: {e}")
