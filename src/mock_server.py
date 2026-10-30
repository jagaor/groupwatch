import threading
import time
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Estado en memoria de los grupos simulados
# Estructura: {nombre_grupo: [lista de miembros (dict con cn, dn, samaccountname)]}
_GROUPS: Dict[str, List[dict]] = {
    "Domain Admins": [
        {"cn": "jsmith", "dn": "CN=jsmith,OU=Users,DC=lab,DC=local", "samaccountname": "jsmith"},
        {"cn": "alopez", "dn": "CN=alopez,OU=Users,DC=lab,DC=local", "samaccountname": "alopez"},
        {"cn": "mgarcia", "dn": "CN=mgarcia,OU=Users,DC=lab,DC=local", "samaccountname": "mgarcia"},
        {"cn": "rperez", "dn": "CN=rperez,OU=Users,DC=lab,DC=local", "samaccountname": "rperez"},
        {"cn": "ltorres", "dn": "CN=ltorres,OU=Users,DC=lab,DC=local", "samaccountname": "ltorres"},
    ],
    "Enterprise Admins": [
        {"cn": "jramirez", "dn": "CN=jramirez,OU=Users,DC=lab,DC=local", "samaccountname": "jramirez"},
        {"cn": "cmendoza", "dn": "CN=cmendoza,OU=Users,DC=lab,DC=local", "samaccountname": "cmendoza"},
        {"cn": "fcastro", "dn": "CN=fcastro,OU=Users,DC=lab,DC=local", "samaccountname": "fcastro"},
        {"cn": "dflores", "dn": "CN=dflores,OU=Users,DC=lab,DC=local", "samaccountname": "dflores"},
    ],
    "Schema Admins": [
        {"cn": "vargas", "dn": "CN=vargas,OU=Users,DC=lab,DC=local", "samaccountname": "vargas"},
        {"cn": "nrojas", "dn": "CN=nrojas,OU=Users,DC=lab,DC=local", "samaccountname": "nrojas"},
        {"cn": "pquiroga", "dn": "CN=pquiroga,OU=Users,DC=lab,DC=local", "samaccountname": "pquiroga"},
    ],
}

app = FastAPI(title="GroupWatch Mock LDAP Server")


class LDAPSearchRequest(BaseModel):
    base_dn: str
    filter: str
    attributes: List[str] = ["cn", "dn", "samaccountname"]


@app.post("/ldap/search")
def ldap_search(req: LDAPSearchRequest):
    """Simula una búsqueda LDAP devolviendo los miembros del grupo indicado.
    El filtro se interpreta de forma laxa: si contiene el nombre de un grupo conocido,
    se devuelven sus miembros; en caso contrario, lista vacía."""
    grupo = None
    for nombre in _GROUPS:
        if nombre.lower() in req.filter.lower() or nombre.lower() in req.base_dn.lower():
            grupo = nombre
            break
    if grupo is None:
        return {"entries": [], "total": 0}
    miembros = _GROUPS[grupo]
    # Proyectar solo los atributos solicitados
    entries = []
    for m in miembros:
        entries.append({k: m[k] for k in req.attributes if k in m})
    return {"entries": entries, "total": len(entries)}


@app.get("/mock/status")
def mock_status():
    """Devuelve el estado actual de todos los grupos simulados."""
    return {"groups": {nombre: miembros for nombre, miembros in _GROUPS.items()}}


def inject_change(group_name: str, action: str, member: dict) -> None:
    """Añade o elimina un miembro del estado en memoria para simular cambios.
    action debe ser 'add' o 'remove'."""
    if group_name not in _GROUPS:
        raise ValueError(f"Grupo desconocido: {group_name}")
    if action == "add":
        if not any(m["samaccountname"] == member["samaccountname"] for m in _GROUPS[group_name]):
            _GROUPS[group_name].append(member)
    elif action == "remove":
        _GROUPS[group_name] = [
            m for m in _GROUPS[group_name]
            if m["samaccountname"] != member["samaccountname"]
        ]
    else:
        raise ValueError("action debe ser 'add' o 'remove'")


def start_mock_server(port: int = 8765) -> threading.Thread:
    """Arranca uvicorn en un hilo daemon y devuelve el hilo."""
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    hilo = threading.Thread(target=server.run, daemon=True)
    hilo.start()
    # Esperar brevemente a que el servidor esté listo
    time.sleep(0.5)
    return hilo
