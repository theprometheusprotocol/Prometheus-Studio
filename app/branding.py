import os


def get_branding():
    """Return branding configuration based on BRAND environment variable.

    Returns a dict with keys: title, logo, favicon, colors, footer.
    Falls back to default branding when BRAND is unset or unrecognized.
    """
    brand = str(os.getenv("BRAND", "default")).strip().lower()

    if brand == "prometheus":
        return {
            "title": "Prometheus Studio",
            "logo": "img/brands/prometheus/logo.png",
            "favicon": "img/brands/prometheus/favicon.png",
            "colors": {
                "primary": "#FF6B00",
                "background": "#0B0B0B",
                "secondary": "#1F1F1F",
                "text": "#FFFFFF",
            },
            "footer": "Prometheus Studio — Evolutionary OS for AI-Human Companies",
        }

    # Default: keep existing CrewAI Studio branding
    return {
        "title": "CrewAI Studio",
        "logo": "img/crewai_logo.png",
        "favicon": "img/favicon.ico",
        "colors": {
            # Not actively used in UI yet; placeholders for future styling
            "primary": "#4F46E5",
            "background": "#FFFFFF",
            "secondary": "#F3F4F6",
            "text": "#111827",
        },
        "footer": "CrewAI Studio",
    }

