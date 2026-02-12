import streamlit as st
import base64
import os

_APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _background_css() -> str:
    """Return background CSS (image or fallback gradient)."""
    bg_css = None
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = os.path.join(_APP_DIR, "assets", f"background.{ext}")
        if os.path.isfile(path):
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            bg_css = f"url(data:{mime};base64,{encoded})"
            break
    if not bg_css:
        bg_css = "linear-gradient(135deg, #e0e7ff 0%, #f0f4ff 50%, #e8f0fe 100%)"
    return f"""
    .stApp {{
        background: {bg_css};
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .stApp > div:first-child {{
        background: rgba(255, 255, 255, 0.85);
    }}
    """


def inject_guest_styles():
    """Inject all CSS for the guest booking wizard."""
    bg = _background_css()
    st.markdown(f"""
    <style>
    {bg}

    /* Hide text inside calendar background events */
    .fc-bg-event {{
        font-size: 0 !important;
        color: transparent !important;
        overflow: hidden !important;
    }}
    .fc-bg-event .fc-event-title,
    .fc-bg-event .fc-event-main,
    .fc-bg-event .fc-event-title-container {{
        display: none !important;
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
    }}
    .hide-event-text,
    .hide-event-text * {{
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
        line-height: 0 !important;
    }}

    /* Narrow centered layout like Calendly */
    .stMainBlockContainer {{
        max-width: 720px;
        margin: 0 auto;
    }}

    /* Step indicator */
    .step-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 1.5rem 0 2rem 0;
        gap: 0;
    }}
    .step {{
        display: flex;
        align-items: center;
    }}
    .step-circle {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.9rem;
        border: 2px solid #ddd;
        color: #999;
        background: #fff;
        flex-shrink: 0;
    }}
    .step-circle.active {{
        border-color: #0069FF;
        color: #fff;
        background: #0069FF;
    }}
    .step-circle.completed {{
        border-color: #0069FF;
        color: #fff;
        background: #0069FF;
    }}
    .step-label {{
        margin: 0 0.5rem;
        font-size: 0.85rem;
        color: #999;
        white-space: nowrap;
    }}
    .step-label.active {{
        color: #1A1A2E;
        font-weight: 600;
    }}
    .step-line {{
        width: 60px;
        height: 2px;
        background: #ddd;
        flex-shrink: 0;
    }}
    .step-line.active {{
        background: #0069FF;
    }}

    /* Status badges */
    .badge {{
        padding: 0.2rem 0.7rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }}
    .badge-pending {{
        background: #FFF3E0;
        color: #E65100;
    }}
    .badge-accepted {{
        background: #E8F5E9;
        color: #2E7D32;
    }}
    .badge-rejected {{
        background: #FFEBEE;
        color: #C62828;
    }}

    /* Mobile responsive */
    @media (max-width: 768px) {{
        .stButton > button {{
            min-height: 48px;
            font-size: 1rem;
        }}
        [data-testid="column"] {{
            min-width: 100% !important;
        }}
        .step-line {{
            width: 30px;
        }}
        .step-label {{
            font-size: 0.75rem;
        }}
    }}

    /* Clean chrome */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)


def inject_admin_styles():
    """Inject CSS for the admin dashboard."""
    st.markdown("""
    <style>
    /* Hide text inside calendar background events */
    .fc-bg-event {
        font-size: 0 !important;
        color: transparent !important;
        overflow: hidden !important;
    }
    .fc-bg-event .fc-event-title,
    .fc-bg-event .fc-event-main,
    .fc-bg-event .fc-event-title-container {
        display: none !important;
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
    }
    .hide-event-text,
    .hide-event-text * {
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
        line-height: 0 !important;
    }

    /* Status badges */
    .badge {
        padding: 0.2rem 0.7rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-pending {
        background: #FFF3E0;
        color: #E65100;
    }
    .badge-accepted {
        background: #E8F5E9;
        color: #2E7D32;
    }
    .badge-rejected {
        background: #FFEBEE;
        color: #C62828;
    }
    </style>
    """, unsafe_allow_html=True)


def render_step_indicator(current_step: int, steps: list[str]):
    """Render a horizontal step progress indicator.

    current_step is 1-indexed (1, 2, or 3).
    """
    html_parts = []
    for i, label in enumerate(steps):
        step_num = i + 1
        if step_num < current_step:
            circle_cls = "completed"
            label_cls = "active"
        elif step_num == current_step:
            circle_cls = "active"
            label_cls = "active"
        else:
            circle_cls = ""
            label_cls = ""

        # Checkmark for completed steps, number for current/future
        content = "&#10003;" if step_num < current_step else str(step_num)

        html_parts.append(
            f'<div class="step">'
            f'<div class="step-circle {circle_cls}">{content}</div>'
            f'<span class="step-label {label_cls}">{label}</span>'
            f'</div>'
        )

        # Add connecting line between steps (not after the last one)
        if step_num < len(steps):
            line_cls = "active" if step_num < current_step else ""
            html_parts.append(f'<div class="step-line {line_cls}"></div>')

    html = f'<div class="step-container">{"".join(html_parts)}</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_status_badge(status: str) -> str:
    """Return HTML string for a colored status badge pill."""
    label = status.title()
    return f'<span class="badge badge-{status}">{label}</span>'
