from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import List


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # libera qualquer site (necessário pro seu caso)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/stream")
async def options_stream():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET",
        }
    )

# fila de eventos (simula comunicação do proxy/IA)
connections = {}

@app.get("/")
def home():
    html = """
    <html>
        <head>
            <style>

                .blurred {
                    filter: blur(6px);
                    pointer-events: none;
                    user-select: none;
                }

                .overlay {
                    position: fixed;
                    top:0;
                    left:0;
                    width:100%;
                    height:100%;
                    background: rgba(0,0,0,0.6);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    z-index:9999;
                }

                .popup {
                    background:white;
                    padding:30px;
                    border-radius:10px;
                    font-family:Arial;
                    max-width:400px;
                    text-align:center;
                }

                button {
                    margin-top:20px;
                    padding:10px 20px;
                    cursor:pointer;
                }

                .redacted {
                    background:black;
                    color:white;
                    padding:2px 6px;
                    border-radius:4px;
                }

            </style>
        </head>

        <body>

            <div id="conteudo">
                <h1>Página Normal</h1>

                <p>
                    Esta página possui uma frase sensível que poderá ser bloqueada
                    dinamicamente pelo servidor.
                </p>
            </div>

          <script>

    console.log("🔌 Iniciando conexão com SSE...");

    // 🔑 clientId (persistente)
    const clientId = localStorage.getItem("clientId") || crypto.randomUUID();
    localStorage.setItem("clientId", clientId);
    
    // 🔑 tabId (único por aba)
    const tabId = sessionStorage.getItem("tabId") || crypto.randomUUID();
    sessionStorage.setItem("tabId", tabId);
    
    console.log("🆔 clientId:", clientId);
    console.log("🧩 tabId:", tabId);
    
    // 🚀 conecta no SSE
    const url = `https://serverssetest-production.up.railway.app/stream?clientId=${clientId}&tabId=${tabId}`;
    const evtSource = new EventSource(url);

    // ✅ conexão aberta
    evtSource.onopen = function () {
        console.log("✅ Conectado ao SSE com sucesso!");
    };

    // 📩 mensagem recebida
    evtSource.onmessage = function (event) {

        console.log("📩 Evento bruto recebido:", event.data);

        if (!event.data || event.data.trim() === "") {
            console.log("💓 Heartbeat recebido (keep-alive)");
            return;
        }

        try {
            const data = JSON.parse(event.data);

            console.log("📦 JSON parseado:", data);

            if (data.type === "highlight") {
                console.log("🚨 Highlight acionado com frases:", data.texts);

                bloquearMultiplasFrases(data.texts);
                aplicarBlurPopup();
            }

        } catch (err) {
            console.error("❌ Erro ao fazer parse do JSON:", err);
        }
    };

    // ❌ erro geral
    evtSource.onerror = function (err) {
        console.error("❌ Erro na conexão SSE:", err);

        if (evtSource.readyState === EventSource.CLOSED) {
            console.error("🔴 Conexão SSE foi fechada");
        } else if (evtSource.readyState === EventSource.CONNECTING) {
            console.warn("🟡 Tentando reconectar ao SSE...");
        }
    };



    function bloquearMultiplasFrases(frases) {

    console.log("🔍 Iniciando bloqueio de frases...");

    const root = document.getElementById("conteudo");

    if (!root) {
        console.warn("⚠️ #conteudo não encontrado, usando document.body");
    }

    const target = root || document.body;

    frases.forEach(frase => {

        console.log("➡️ Procurando frase:", frase);

        const walker = document.createTreeWalker(
            target,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        let node;

        while (node = walker.nextNode()) {

            const texto = node.nodeValue;

            if (texto.includes(frase)) {

                console.log("🚫 Frase encontrada:", frase);

                const partes = texto.split(frase);
                const fragment = document.createDocumentFragment();

                partes.forEach((parte, index) => {

                    fragment.appendChild(
                        document.createTextNode(parte)
                    );

                    if (index < partes.length - 1) {

                        const span = document.createElement("span");
                        span.className = "redacted";
                        span.textContent = "[redacted]";

                        fragment.appendChild(span);
                    }
                });

                node.parentNode.replaceChild(fragment, node);
            }
        }
    });

    console.log("✅ Bloqueio concluído");
}



    function aplicarBlurPopup() {

        console.log("🌀 Aplicando blur + popup");

        const conteudo = document.getElementById("conteudo") || document.body;

        conteudo.classList.add("blurred");
        
        const overlay = document.createElement("div");
        overlay.className = "overlay";

        const popup = document.createElement("div");
        popup.className = "popup";

        popup.innerHTML = `
            <h2>Conteúdo bloqueado</h2>
            <p>Algumas palavras foram ocultadas automaticamente.</p>
            <button id="fechar">Entendi</button>
        `;

        overlay.appendChild(popup);
        document.body.appendChild(overlay);

        document.getElementById("fechar").onclick = () => {
            console.log("🟢 Usuário fechou o popup");

            overlay.remove();
            document.getElementById("conteudo").classList.remove("blurred");
        };
    }

</script>

        </body>
    </html>
    """
    return HTMLResponse(html)


@app.get("/stream")
async def stream(request: Request, clientId: str, tabId: str):

    if clientId not in connections:
        connections[clientId] = {}

    if tabId not in connections[clientId]:
        connections[clientId][tabId] = asyncio.Queue()

    queue = connections[clientId][tabId]
    print(f"🟢 Conectado: client={clientId} tab={tabId}")

    async def event_generator():
        yield "retry: 300\n\n"  # 🔥 importante (abre conexão rápido)
        yield ":\n\n"            # abre conexão
    
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=5)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                yield ":\n\n"  # 🔥 heartbeat constante
            except Exception as e:
                print("❌ Erro no stream:", str(e))
                break
                
            finally:
                # 🔥 remove quando desconectar
                print(f"🔴 Desconectado: {clientId} | {tabId}")
                connections.get(clientId, {}).pop(tabId, None)
        
                # 🔥 limpa client vazio
                if clientId in connections and not connections[clientId]:
                    connections.pop(clientId)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET",
        }
    )



# 🔥 simula o PROXY/IA terminando o processamento

@app.post("/proxy-result")
async def proxy_result(frases: List[str]):

    payload = {
        "type": "highlight",
        "texts": frases
    }

    data = json.dumps(payload)

    print("📡 Broadcast para todos")

    for client in connections.values():
        for queue in client.values():
            await queue.put(data)

    return {"status": "broadcast sent"}

@app.post("/send-to-client")
async def send_to_client(clientId: str, frases: List[str]):

    payload = {
        "type": "highlight",
        "texts": frases
    }

    data = json.dumps(payload)

    if clientId in connections:
        for queue in connections[clientId].values():
            await queue.put(data)

    return {"status": "sent to client"}

@app.post("/send-to-tab")
async def send_to_tab(clientId: str, tabId: str, frases: List[str]):

    payload = {
        "type": "highlight",
        "texts": frases
    }

    data = json.dumps(payload)

    if clientId in connections:
        if tabId in connections[clientId]:
            await connections[clientId][tabId].put(data)

    return {"status": "sent to tab"}
