#import
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
import os, json, fcntl
from contextlib import contextmanager

#coisas que vou usar aq

DB_PATH = '/data/db.json'
PREFIXO = 'C'    
RAZAO_PREF = 2      
TZ_BR = timezone(timedelta(hours=-3))

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
if not os.path.exists(DB_PATH):
    with open(DB_PATH, 'w') as f:
        json.dump({"hoje": "", "seq": 0, "consec_pref": 0, "senhas": []}, f)

def get_agora():
    return datetime.now(TZ_BR)

@contextmanager
def gerenciar_banco(somente_leitura=False):
    modo = 'r' if somente_leitura else 'r+'
    trava = fcntl.LOCK_SH if somente_leitura else fcntl.LOCK_EX
    
    with open(DB_PATH, modo) as f:
        fcntl.flock(f, trava)
        try:
            db = json.load(f)
            yield db
            if not somente_leitura:
                f.seek(0)
                f.truncate()
                json.dump(db, f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

#rotas

app = FastAPI()

@app.get("/healthz")
def healthz():
    return JSONResponse(content={"status": "ok"})

@app.post("/senhas")
async def gerar_senha(request: Request):
    try:
        dados = await request.json()
    except json.JSONDecodeError:
        dados = {}
        
    tipo = dados.get("tipo")
    if tipo not in ["normal", "preferencial"]:
        return JSONResponse(content={"erro": "tipo_invalido"}, status_code=422)
        
    agora = get_agora()
    hoje_str = agora.strftime('%Y-%m-%d')
    emissao = agora.isoformat(timespec='seconds')
    
    with gerenciar_banco() as db:
        if db["hoje"] != hoje_str:
            db["hoje"] = hoje_str
            db["seq"] = 0
            
        db["seq"] += 1
        codigo = f"{PREFIXO}{db['seq']:03d}"
        
        senha = {
            "codigo": codigo, 
            "tipo": tipo, 
            "status": "aguardando",
            "emissao": emissao
        }
        db["senhas"].append(senha)
        
    return JSONResponse(content=senha, status_code=201)

@app.get("/senhas/proxima")
def chamar_proxima():
    with gerenciar_banco() as db:
        aguardando = [s for s in db["senhas"] if s["status"] == "aguardando"]
        pref = [s for s in aguardando if s["tipo"] == "preferencial"]
        norm = [s for s in aguardando if s["tipo"] == "normal"]
        
        escolhida = None
        
        if db["consec_pref"] < RAZAO_PREF:
            if pref:
                escolhida = pref[0]
                db["consec_pref"] += 1
            elif norm:
                escolhida = norm[0]
                db["consec_pref"] = 0
        else:
            if norm:
                escolhida = norm[0]
                db["consec_pref"] = 0
            elif pref:
                escolhida = pref[0]
                db["consec_pref"] += 1
                
        if not escolhida:
            return JSONResponse(content={"erro": "fila_vazia"}, status_code=404)
            
        escolhida["status"] = "chamada"
        escolhida["chamada_em"] = get_agora().isoformat(timespec='seconds')
        
    return JSONResponse(content=escolhida, status_code=200)

@app.post("/senhas/{codigo}/concluir")
def concluir(codigo: str):
    with gerenciar_banco() as db:
        senha = next((s for s in db["senhas"] if s["codigo"] == codigo), None)
        if not senha: 
            return JSONResponse(content={"erro": "senha_nao_encontrada"}, status_code=404)
        if senha["status"] != "chamada": 
            return JSONResponse(content={"erro": "senha_nao_chamada"}, status_code=409)
        
        senha["status"] = "concluida"
    return JSONResponse(content=senha, status_code=200)

@app.post("/senhas/{codigo}/rechamar")
def rechamar(codigo: str):
    with gerenciar_banco() as db:
        senha = next((s for s in db["senhas"] if s["codigo"] == codigo), None)
        if not senha: 
            return JSONResponse(content={"erro": "senha_nao_encontrada"}, status_code=404)
        if senha["status"] != "chamada": 
            return JSONResponse(content={"erro": "senha_nao_chamada"}, status_code=409)
        
        senha["chamada_em"] = get_agora().isoformat(timespec='seconds')
    return JSONResponse(content=senha, status_code=200)