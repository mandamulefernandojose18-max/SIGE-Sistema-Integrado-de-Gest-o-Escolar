from django.contrib import admin

from .models import MensagemContacto


@admin.register(MensagemContacto)
class MensagemContactoAdmin(admin.ModelAdmin):
    list_display = ('assunto', 'nome', 'email', 'lida', 'created_at')
    list_filter = ('lida',)
    search_fields = ('assunto', 'nome', 'email')
    readonly_fields = ('nome', 'email', 'assunto', 'mensagem', 'created_at')
