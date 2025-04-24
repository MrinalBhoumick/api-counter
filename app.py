import streamlit as st
import json
import re
from collections import defaultdict
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font

st.set_page_config(page_title="API Explorer", layout="wide")
st.title("🔍 API Structure Explorer")
st.markdown("Upload a **Postman Collection** or **OpenAPI/Swagger JSON** file to explore APIs, view env variables, and request bodies.")

# Utility to extract Postman-style env vars like {{...}}
def extract_variables(text):
    return re.findall(r"{{(.*?)}}", text) if isinstance(text, str) else []

# 📦 Parse Postman Collection
def parse_postman(data):
    folder_api_map = defaultdict(list)
    all_variables = set()
    total = 0

    def traverse(items, path=""):
        nonlocal total
        for item in items:
            name = item.get("name", "Unnamed")
            if 'request' in item:
                request = item['request']
                api_info = {"name": name}

                variables = set()

                # URL
                url = request.get("url", {}).get("raw", "")
                variables.update(extract_variables(url))
                api_info["path"] = url

                # Headers
                for h in request.get("header", []):
                    variables.update(extract_variables(h.get("value", "")))

                # Body
                body = request.get("body", {})
                if "raw" in body:
                    raw_body = body.get("raw", "")
                    variables.update(extract_variables(raw_body))
                    api_info["body"] = raw_body

                api_info["variables"] = sorted(list(variables))
                all_variables.update(variables)

                folder_api_map[path].append(api_info)
                total += 1

            elif 'item' in item:
                sub_path = f"{path}/{item['name']}" if path else item['name']
                traverse(item['item'], sub_path)

    traverse(data.get("item", []))
    return folder_api_map, total, all_variables

# 📘 Parse OpenAPI/Swagger
def parse_openapi(data):
    folder_api_map = defaultdict(list)
    all_variables = set()
    total = 0

    paths = data.get("paths", {})
    for endpoint, methods in paths.items():
        for method, details in methods.items():
            tag = details.get("tags", ["Untagged"])[0]
            summary = details.get("summary", f"{method.upper()} {endpoint}")

            api_info = {
                "name": f"{method.upper()} {endpoint} — {summary}",
                "path": endpoint,
                "variables": extract_variables(endpoint)
            }
            all_variables.update(api_info["variables"])

            # Request body if present
            request_body = details.get("requestBody", {})
            content = request_body.get("content", {})
            if "application/json" in content:
                example = content["application/json"].get("example")
                if example:
                    api_info["body"] = json.dumps(example, indent=2)

            folder_api_map[tag].append(api_info)
            total += 1

    return folder_api_map, total, all_variables

# 🚀 File Upload UI
uploaded_file = st.file_uploader("📤 Upload your Postman/OpenAPI JSON file", type="json")

if uploaded_file:
    try:
        data = json.load(uploaded_file)

        folder_api_map = defaultdict(list)
        total = 0
        all_variables = set()

        if "item" in data:
            folder_api_map, total, all_variables = parse_postman(data)
            st.subheader("📂 Postman Collection: Folder-wise APIs")

        elif "paths" in data:
            folder_api_map, total, all_variables = parse_openapi(data)
            st.subheader("📂 OpenAPI/Swagger: Tag-wise APIs")

        else:
            st.error("❌ Unsupported format. Please upload a valid Postman or OpenAPI JSON file.")

        # 🔍 Search Feature
        search_term = st.text_input("🔍 Search for API (by name or method)")

        # Filter APIs based on search term
        filtered_apis = defaultdict(list)
        for folder, apis in folder_api_map.items():
            for api in apis:
                if search_term.lower() in api["name"].lower():
                    filtered_apis[folder].append(api)

        # Render filtered APIs
        for folder, apis in filtered_apis.items():
            with st.expander(f"📁 {folder} — {len(apis)} APIs"):
                for api in apis:
                    st.markdown(f"**• {api['name']}**")
                    if api.get("path"):
                        st.markdown(f"  - 🌐 Path: `{api['path']}`")
                    if api.get("variables"):
                        st.markdown(f"  - 🔑 Env Vars: `{', '.join(api['variables'])}`")
                    if api.get("body"):
                        st.markdown("  - 📦 Request Body:")
                        st.code(api["body"], language="json")

        st.success(f"✅ Total API requests found: {total}")
        if all_variables:
            st.info(f"🌐 Unique environment variables used: `{', '.join(sorted(all_variables))}`")

        # 📥 Export to Excel
        if total > 0:
            export_data = []
            for folder, apis in filtered_apis.items():
                for api in apis:
                    export_data.append({
                        "Folder/Tag": folder,
                        "API Name": api["name"],
                        "API Path": api.get("path", ""),
                        "Env Variables": ", ".join(api.get("variables", [])),
                        "Request Body": api.get("body", ""),
                    })

            if export_data:
                df = pd.DataFrame(export_data)
                buffer = BytesIO()
                wb = Workbook()
                ws = wb.active
                ws.title = "API Details"

                for row in dataframe_to_rows(df, index=False, header=True):
                    ws.append(row)

                # Bold headers
                for cell in ws[1]:
                    cell.font = Font(bold=True)

                # Auto-adjust column widths
                for col in ws.columns:
                    max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
                    ws.column_dimensions[col[0].column_letter].width = max_length + 2

                wb.save(buffer)
                buffer.seek(0)

                st.download_button(
                    label="📥 Export as Excel",
                    data=buffer,
                    file_name="api_details.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Error parsing file: {str(e)}")
