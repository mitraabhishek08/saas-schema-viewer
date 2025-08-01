import streamlit as st
import requests

st.title("Schema Viewer")

# Initialize session state variables
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "login_success" not in st.session_state:
    st.session_state.login_success = False
if "metadata" not in st.session_state:
    st.session_state.metadata = None


# Environment URLs mapping
ENVIRONMENTS = {
    "TechSales": {
        "login_url": "https://dmp-us.informaticacloud.com/saas/public/core/v3/login",
        "metadata_url": "https://usw1-mdm.dmp-us.informaticacloud.com/metadata/api/v2/objects/tenantModel/datamodel",
    },
    "Global Generic Demo": {
        "login_url": "https://dm-us.informaticacloud.com/saas/public/core/v3/login",
        "metadata_url": "https://use6-mdm.dm-us.informaticacloud.com/metadata/api/v2/objects/tenantModel/datamodel",
    },
}


def fetch_session_id(username, password, login_url):
    login_payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/json"}
    response = requests.post(login_url, json=login_payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get("userInfo", {}).get("sessionId")


def fetch_metadata(session_id, metadata_url):
    metadata_headers = {"IDS-SESSION-ID": session_id}
    response = requests.get(metadata_url, headers=metadata_headers)
    response.raise_for_status()
    return response.json()


def build_dot_for_entity(target_entity):
    root_name = target_entity.get("name", "Unknown")
    fields = target_entity.get("field", [])

    direct_lookups = []
    field_groups = {}

    for field in fields:
        label_obj = field.get("label", {})
        field_name = label_obj.get("en") if label_obj else None
        if not field_name:
            continue

        if "codeField" in field:
            if field_name not in direct_lookups:
                direct_lookups.append(field_name)

        elif field.get("allowMany") is True:
            if field_name not in field_groups:
                field_groups[field_name] = []
            nested_fields = field.get("field", [])
            for nf in nested_fields:
                nf_label = nf.get("label", {})
                nf_name = nf_label.get("en") if nf_label else None
                if nf_name and "codeField" in nf:
                    if nf_name not in field_groups[field_name]:
                        field_groups[field_name].append(nf_name)

    dot = "digraph ER {\n"
    dot += "  rankdir=LR;\n"
    dot += '  node [shape=record, style="filled,rounded"];\n'
    dot += f'  "{root_name}" [label="{root_name}", fillcolor=lightblue];\n'

    for lookup in direct_lookups:
        dot += f'  "{lookup}" [label="{lookup}", fillcolor=lightyellow];\n'
        dot += f'  "{root_name}" -> "{lookup}" [label="lookup"];\n'

    for fg_name, fg_lookups in field_groups.items():
        dot += f'  "{fg_name}" [label="{fg_name}", fillcolor="#B39EB5"];\n'
        dot += f'  "{root_name}" -> "{fg_name}" [label="field group"];\n'

        for nested_lookup in fg_lookups:
            nested_lookup_node = f"{fg_name}::{nested_lookup}"
            dot += f'  "{nested_lookup_node}" [label="{nested_lookup}", fillcolor=orange];\n'
            dot += f'  "{fg_name}" -> "{nested_lookup_node}" [label="lookup"];\n'

    dot += "}"
    return dot, root_name


def build_relationships_dot(selected_entities, business_entities, relationships):
    guid_to_name = {}
    for entity in business_entities:
        guid = entity.get("guid")
        name = entity.get("name") or guid
        guid_to_name[guid] = name

    selected_names = set(selected_entities)

    dot = "digraph Relationships {\n"
    dot += "  rankdir=LR;\n"
    dot += '  node [shape=record, style="filled,rounded", fillcolor="#FACDA0"];\n'

    for name in selected_entities:
        dot += f'  "{name}";\n'

    rel_graphs = [r for r in relationships if r.get("storage") == "graph"]

    for rel in rel_graphs:
        rel_name = rel.get("name", "")
        from_obj = rel.get("from", {})
        to_obj = rel.get("to", {})
        options = rel.get("options", {})
        direction = options.get("direction", "FORWARD").upper()

        from_guid = from_obj.get("businessEntity", {}).get("$ref")
        to_guid = to_obj.get("businessEntity", {}).get("$ref")

        from_name = guid_to_name.get(from_guid)
        to_name = guid_to_name.get(to_guid)

        if from_name in selected_names and to_name in selected_names:
            if direction == "FORWARD":
                dot += f'  "{from_name}" -> "{to_name}" [label="{rel_name}"];\n'
            elif direction == "BACKWARD":
                dot += f'  "{to_name}" -> "{from_name}" [label="{rel_name}"];\n'
            elif direction == "BIDIRECTED":
                dot += f'  "{from_name}" -> "{to_name}" [dir="both", label="{rel_name}"];\n'
            else:
                dot += f'  "{from_name}" -> "{to_name}" [label="{rel_name}"];\n'

    dot += "}"
    return dot


def build_single_entity_relationships_dot(entity_guid, business_entities, relationships):
    guid_to_name = {}
    for entity in business_entities:
        guid = entity.get("guid")
        name = entity.get("name") or guid
        guid_to_name[guid] = name

    entity_name = guid_to_name.get(entity_guid, "Unknown")

    dot = "digraph SingleEntityRelationships {\n"
    dot += "  rankdir=LR;\n"
    dot += '  node [shape=record, style="filled,rounded", fillcolor="#FACDA0"];\n'

    dot += f'  "{entity_name}";\n'

    rel_graphs = [r for r in relationships if r.get("storage") == "graph"]

    for rel in rel_graphs:
        rel_name = rel.get("name", "")
        from_obj = rel.get("from", {})
        to_obj = rel.get("to", {})
        options = rel.get("options", {})
        direction = options.get("direction", "FORWARD").upper()

        from_guid = from_obj.get("businessEntity", {}).get("$ref")
        to_guid = to_obj.get("businessEntity", {}).get("$ref")

        if entity_guid == from_guid or entity_guid == to_guid:
            from_name = guid_to_name.get(from_guid)
            to_name = guid_to_name.get(to_guid)

            if from_guid != entity_guid:
                dot += f'  "{from_name}";\n'
            if to_guid != entity_guid:
                dot += f'  "{to_name}";\n'

            if direction == "FORWARD":
                dot += f'  "{from_name}" -> "{to_name}" [label="{rel_name}"];\n'
            elif direction == "BACKWARD":
                dot += f'  "{to_name}" -> "{from_name}" [label="{rel_name}"];\n'
            elif direction == "BIDIRECTED":
                dot += f'  "{from_name}" -> "{to_name}" [dir="both", label="{rel_name}"];\n'
            else:
                dot += f'  "{from_name}" -> "{to_name}" [label="{rel_name}"];\n'

    dot += "}"
    return dot


# -- Login --
if not st.session_state.login_success:
    selected_env = st.radio("Select Environment", options=["TechSales", "Global Generic Demo"], index=0)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Log In"):
        if not username or not password:
            st.error("Please enter both username and password.")
        else:
            login_url = ENVIRONMENTS[selected_env]["login_url"]
            metadata_url = ENVIRONMENTS[selected_env]["metadata_url"]
            try:
                session_id = fetch_session_id(username, password, login_url)
                if session_id:
                    st.session_state.session_id = session_id
                    st.session_state.login_success = True
                    st.session_state.metadata_url = metadata_url
                    st.success("Login successful!")
                    with st.spinner("Loading metadata, please wait..."):
                        st.session_state.metadata = fetch_metadata(session_id, metadata_url)
                else:
                    st.error("Failed to retrieve session ID.")
            except requests.exceptions.HTTPError as e:
                st.error(f"HTTP error: {e}")
            except Exception as e:
                st.error(f"Error occurred: {e}")


EXCLUDE_GUIDS = {"p360.classification"}

# -- After Login --
if st.session_state.login_success:
    if st.session_state.metadata is None:
        st.error("Metadata not loaded. Please log in again.")
    else:
        metadata = st.session_state.metadata
        business_entities = metadata.get("businessEntity", [])
        relationships = metadata.get("relationship", [])

        filtered_entities = [
            e for e in business_entities if e.get("storage") == "ent" and e.get("guid") not in EXCLUDE_GUIDS
        ]

        name_guid_map = {}
        for i, ent in enumerate(filtered_entities):
            name = ent.get("name") or ent.get("guid") or f"Unknown-{i}"
            name_guid_map[name] = ent.get("guid")

        entity_names = list(name_guid_map.keys())

        entity_choices = st.multiselect(
            "Select entities to visualize", options=entity_names, default=entity_names[:3]
        )

        if st.button("Visualize MDM Schema"):
            if not entity_choices:
                st.error("Select at least one entity to visualize.")
            elif len(entity_choices) == 1:
                entity_name = entity_choices[0]
                guid = name_guid_map[entity_name]
                target_entity = next((e for e in filtered_entities if e.get("guid") == guid), None)
                if not target_entity:
                    st.error(f"Entity with guid '{guid}' not found.")
                else:
                    dot, root_name = build_dot_for_entity(target_entity)
                    st.subheader(f"Entity: {root_name}")
                    st.graphviz_chart(dot)

                    rel_dot = build_single_entity_relationships_dot(guid, filtered_entities, relationships)
                    st.subheader("Relationships of this entity")
                    st.graphviz_chart(rel_dot)
            else:
                dot = build_relationships_dot(entity_choices, filtered_entities, relationships)
                st.subheader("Relationships between selected entities")
                st.graphviz_chart(dot)


if not st.session_state.login_success:
    st.info("Please log in to access and visualize MDM metadata.")
