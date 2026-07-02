# Despliegue rápido en VM (Oracle Always Free)

Pasos para poner el bot en una VM Always Free de Oracle (Linux, p. ej. Ubuntu):

1. Crea una instancia ARM/AMD Always Free y conéctate por SSH.

2. Clona el repo y sitúalo en `/home/ubuntu/bot-facturas`:

```bash
git clone <tu-repo-url> bot-facturas
cd bot-facturas
```

3. Crea `.env` (copia `.env.example`) y configura las variables: `TELEGRAM_BOT_TOKEN`, `GOOGLE_*`, `DRY_RUN=0` en producción.

4. Crea un entorno virtual e instala dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

5. (opcional) Probar localmente:

```bash
.venv/bin/python src/bot.py
```

6. Instalar el servicio `systemd` (ejemplo en `deploy/bot.service`):

```bash
sudo cp deploy/bot.service /etc/systemd/system/bot-facturas.service
# Ajusta User, WorkingDirectory y EnvironmentFile si es necesario
sudo systemctl daemon-reload
sudo systemctl enable --now bot-facturas.service
sudo journalctl -u bot-facturas.service -f
```

7. Alternativa con Docker (no requiere virtualenv):

```bash
docker build -t bot-facturas:latest .
# Ejecutar usando un fichero de entorno
docker run -d --env-file .env --name bot-facturas bot-facturas:latest
docker logs -f bot-facturas
```

Notas:
- Guarda las credenciales sensibles en `~/.oci` o en el servicio de secretos que uses; no las subas al repo.
- Si usas Google OAuth, la primera ejecución pedirá autorización (abrir navegador). Para VM headless usa `service_account` si es posible.
