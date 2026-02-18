def get_contrast_color(hex_color):
    """
    Retourne la couleur de texte (blanc ou noir) contrastant le mieux avec la couleur de fond hexadécimale.
    """
    if not hex_color or not hex_color.startswith('#'):
        return "#000000"
    
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        # Calcul de la luminance (formule standard)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#FFFFFF"
    except (ValueError, IndexError):
        return "#000000"
