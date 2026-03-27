"""
Custom styling utilities for the simulator view.
"""

# Color definitions
CHECKBOX_COLOR = "#2C3770"
TEXT_SELECTED_COLOR = "#E0EAFF"
TEXT_SELECTED_BG = "#2C377015"  # semi-transparent background
BORDER_COLOR = "#94B6FF"


def _bullets_to_html_list(content: str) -> str:
    """Convert markdown bullet lines into a HTML list for reliable rendering in custom containers."""
    items = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        items.append(line)

    if not items:
        return ""

    li_html = "".join(f"<li>{item}</li>" for item in items)
    return f"<ul style=\"margin: 0; padding-left: 18px;\">{li_html}</ul>"

def inject_checkbox_styles():
    """Injects custom CSS for checkbox styling."""
    import streamlit as st
    
    css = f"""
    <style>
        /* Custom checkbox accent color */
        [data-testid="stCheckbox"] > label > div:first-child {{
            accent-color: {CHECKBOX_COLOR} !important;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def get_selected_text_style() -> str:
    """Returns styled text wrapper for selected items in Simulator Suggestions."""
    return f'<span style="color: {TEXT_SELECTED_COLOR}; background-color: {TEXT_SELECTED_BG}; padding: 2px 6px; border-radius: 3px;">'

def get_detail_box_html(content: str) -> str:
    """Returns HTML for the details box with styling."""
    list_html = _bullets_to_html_list(content)
    return f"""
    <div style="border: 2px solid {BORDER_COLOR}; 
                padding: 12px; 
                border-radius: 5px;
                background-color: rgba(45, 55, 112, 0.03);
                font-size: 14px;
                line-height: 1.8;">
        {list_html}
    </div>
    """

def get_checkbox_label_html(label: str, is_selected: bool = False) -> str:
    """Generate styled label text for checkbox."""
    if is_selected:
        style = f'style="color: {TEXT_SELECTED_COLOR}; background-color: {TEXT_SELECTED_BG}; padding: 2px 4px; border-radius: 2px;"'
        return f'<span {style}>{label}</span>'
    return label
