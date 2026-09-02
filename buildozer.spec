[app]

# Nome que aparece no launcher
title = Endpoint Home

# Nome do pacote e dominio (troque o dominio pelo seu)
package.name = endpointhome
package.domain = br.com.inorpel

source.dir = .
source.include_exts = py,png,jpg,kv,json

version = 1.0

# Dependencias. stdlib cobre o servidor; plyer+pyjnius fazem a telemetria.
requirements = python3,kivy==2.3.0,plyer,pyjnius,android

orientation = portrait
fullscreen = 0

# Permissoes:
# INTERNET / ACCESS_NETWORK_STATE  -> enviar e receber na rede
# ACCESS_WIFI_STATE                -> ler SSID/IP/RSSI
# ACCESS_FINE_LOCATION             -> Android 9+ exige p/ expor o SSID
# FOREGROUND_SERVICE + WAKE_LOCK   -> manter o agente vivo (uso futuro)
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,ACCESS_FINE_LOCATION,FOREGROUND_SERVICE,WAKE_LOCK

# API alvo/minima
android.api = 34
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a

# Aceita as licencas do SDK automaticamente no CI
android.accept_sdk_license = True

# Sem tela cheia, permite o app aparecer normal
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
