from datetime import datetime

def register_filters(app):
    @app.template_filter("contrast_color")
    def get_contrast_color(hex_color):
        hex_color = hex_color.lstrip('#')
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except (ValueError, IndexError):
            return '#ffffff'
        yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
        return '#000000' if yiq >= 128 else '#ffffff'

    @app.template_filter("freshness_badge")
    def freshness_badge_filter(date_value):
        if not date_value:
            return {"text": "À revoir", "class": "bg-warning"}
        
        if isinstance(date_value, str):
            try:
                from dateutil import parser
                date_value = parser.parse(date_value)
            except:
                return {"text": "À revoir", "class": "bg-warning"}
        
        now = datetime.now()
        if date_value.tzinfo:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        
        delta = now - date_value
        days = delta.days
        
        if days < 30:
            return {"text": "Récent", "class": "bg-success"}
        elif days < 180:
            return {"text": "À jour", "class": "bg-info"}
        else:
            return {"text": "À revoir", "class": "bg-warning"}

    @app.template_filter("format_date")
    def format_date(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
            return d
