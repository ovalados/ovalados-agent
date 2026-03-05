# Ovalados Agent 🏉

Script que corre automáticamente cada 2 horas, obtiene resultados de Super Rugby Américas desde ESPN y los escribe a Firebase.

---

## Setup (15 minutos)

### 1. Crear repositorio en GitHub

1. Entrá a [github.com](https://github.com)
2. Click en **New repository**
3. Nombre: `ovalados-agent`
4. Privado (recomendado)
5. Click **Create repository**
6. Subí estos archivos (arrastrá la carpeta o usá `git push`)

### 2. Conseguir el Firebase Secret

1. Entrá a [console.firebase.google.com](https://console.firebase.google.com)
2. Tu proyecto → **Configuración del proyecto** (ícono de engranaje)
3. Pestaña **Cuentas de servicio**
4. Bajá hasta **Database secrets** → **Mostrar** → copiá el token

### 3. Configurar GitHub Secrets

En tu repo de GitHub:

1. **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**

Agregá estos dos secrets:

| Nombre | Valor |
|--------|-------|
| `FIREBASE_URL` | `https://ovalados-6c645-default-rtdb.firebaseio.com` |
| `FIREBASE_SECRET` | el token que copiaste de Firebase |

### 4. Activar GitHub Actions

1. En tu repo → pestaña **Actions**
2. Click **Enable workflows** si aparece el botón
3. Entrá al workflow **Ovalados — Fetch Results**
4. Click **Run workflow** para probarlo manualmente

---

## Cómo funciona

```
GitHub Actions (cada 2hs)
        ↓
  fetch_results.py
        ↓
  ESPN API (scoreboard + standings)
        ↓
  Parsea resultados y tabla
        ↓
  Firebase Realtime Database
        ↓
  super-rugby.html lee los datos en tiempo real
```

## Estructura Firebase

```
superrugby/
  meta/
    lastUpdate: "2026-03-04T18:00:00Z"
    matchesPlayed: 8
    source: "espn/slar"
  standings/
    Capibaras XV: { pts: 10, pj: 2, g: 2, ... }
    Tarucas: { pts: 9, ... }
    ...
  matches/
    Tarucas_vs_Selknam_2026-02-20: { hs: 41, as: 13, played: true }
    ...
```

## Correr localmente (para testear)

```bash
pip install requests

export FIREBASE_URL="https://ovalados-6c645-default-rtdb.firebaseio.com"
export FIREBASE_SECRET="tu-secret"

python scripts/fetch_results.py
```

## Próximos pasos

Para que `super-rugby.html` **lea** estos datos de Firebase en tiempo real, hay que agregar el SDK de Firebase al HTML y reemplazar el array `teams` y `matches` hardcodeados por lecturas de la DB.
