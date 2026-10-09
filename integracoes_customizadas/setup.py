from integracoes_customizadas.provas.setup import after_install as install_provas
from integracoes_customizadas.whatsapp.setup import ensure_notification_field


def after_install():
	install_provas()
	ensure_notification_field()
