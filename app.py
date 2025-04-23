import streamlit as st
import json
from collections import defaultdict

st.set_page_config(page_title="API Explorer", layout="wide")

st.title("🧪 API Folder Explorer")
st.markdown("Upload your **Postman Collection** or **Swagger/OpenAPI JSON** file to explore your APIs.")


def traverse_postman_items(items, folder_path="", folder_api_map=None):
    count = 0
    for item in items:
        name = item.get("name", "Unnamed")
        if "request" in item:
            folder_api_map[folder_path].append(name)
            count += 1
        elif "item" in item:
            subfolder = f"{folder_path}/{name}" if folder_path else name
            count += traverse_postman_items(item["item"], subfolder, folder_api_map)
    return count


uploaded_file = st.file_uploader("📤 Upload your JSON file", type="json")

if uploaded_file:
    try:
        data = json.load(uploaded_file)
        folder_api_map = defaultdict(list)

        if "item" in data:  # Postman Collection
            total = traverse_postman_items(data["item"], folder_api_map=folder_api_map)

            st.subheader("📂 Folder-wise API Count")
            for folder, apis in folder_api_map.items():
                st.markdown(f"**{folder}** - {len(apis)} APIs")
                for api in apis:
                    st.markdown(f"- {api}")
                st.markdown("---")

            st.success(f"✅ Total API requests found: {total}")

        elif "paths" in data:  
            st.warning("Swagger/OpenAPI format detected. Parsing not yet implemented.")

        else:
            st.error("Unsupported file format. Only Postman Collections and Swagger/OpenAPI JSON files are supported.")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
