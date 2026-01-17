"""
Streamlit UI styling constants.

Contains all custom CSS styling for the TaskTriage Streamlit application.
"""

# Custom CSS for professional styling
CUSTOM_CSS = """
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

    /* Left panel styling */
    [data-testid="column"]:first-child {
        background-color: #1e1e2e;
        border-radius: 8px;
        padding: 1rem;
    }

    /* Section headers */
    .section-header {
        color: #cdd6f4;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid #45475a;
    }

    /* File list container */
    .file-list-container {
        background-color: #313244;
        border-radius: 6px;
        padding: 0.5rem;
        max-height: 200px;
        overflow-y: auto;
    }

    /* File item styling */
    .file-item {
        padding: 0.4rem 0.6rem;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.85rem;
        color: #cdd6f4;
        margin-bottom: 2px;
    }

    .file-item:hover {
        background-color: #45475a;
    }

    .file-item.selected {
        background-color: #89b4fa;
        color: #1e1e2e;
    }

    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 500;
    }

    /* Primary triage button */
    .triage-button > button {
        background-color: #89b4fa;
        color: #1e1e2e;
        font-size: 1.1rem;
        padding: 0.75rem;
    }

    .triage-button > button:hover {
        background-color: #b4befe;
    }

    /* Editor panel */
    .editor-panel {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Editor header */
    .editor-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #e0e0e0;
    }

    /* Monospace text area */
    .stTextArea textarea {
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* Status indicator */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 0.5rem;
    }

    .status-saved {
        background-color: #a6e3a1;
    }

    .status-unsaved {
        background-color: #f38ba8;
    }

    /* Progress container */
    .progress-container {
        background-color: #313244;
        border-radius: 6px;
        padding: 1rem;
        margin-top: 1rem;
    }

    .progress-item {
        color: #cdd6f4;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
    }

    /* Markup buttons */
    .markup-buttons {
        display: flex;
        gap: 0.5rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Toast styling */
    .stToast {
        background-color: #313244;
        color: #cdd6f4;
    }
</style>
"""
