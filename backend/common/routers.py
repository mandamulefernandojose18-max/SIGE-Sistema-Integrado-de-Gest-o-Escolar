from rest_framework.routers import DefaultRouter

class OptionalSlashRouter(DefaultRouter):
    """
    Router DRF customizado que aceita URLs com barra opcional (ex: /escolas e /escolas/).
    Evita redirecionamentos HTTP 301 em requisições POST/PUT do Frontend SPA.
    Usa '(?:/)?' para compatibilidade total com format_suffix_patterns do DRF.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = '(?:/)?'

