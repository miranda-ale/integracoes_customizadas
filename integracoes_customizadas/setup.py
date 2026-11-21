from integracoes_customizadas.bionexo.setup import garantir_campos_na_instalacao
from integracoes_customizadas.provas.setup import after_install as install_provas
from integracoes_customizadas.whatsapp.setup import ensure_notification_field


def after_install():
	install_provas()
	ensure_notification_field()
	garantir_campos_na_instalacao()
