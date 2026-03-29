from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
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

# fila de eventos (simula comunicação do proxy/IA)
event_queue = asyncio.Queue()

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

    const url = "https://serverssetest-production.up.railway.app/stream";
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

        frases.forEach(frase => {

            console.log("➡️ Procurando frase:", frase);

            const walker = document.createTreeWalker(
                document.getElementById("conteudo"),
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            let node;

            while (node = walker.nextNode()) {

                const texto = node.nodeValue;

                if (texto.includes(frase)) {

                    console.log("🚫 Frase encontrada no texto:", texto);

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

        document.getElementById("conteudo").classList.add("blurred");

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
async def stream():

    async def event_generator():
        yield ":\n\n"  # comentário inicial para evitar timeout imediato
        while True:
            try:
                data = await asyncio.wait_for(event_queue.get(), timeout=15)

                yield f"data: {data}\n\n"
                await asyncio.sleep(0)

            except asyncio.TimeoutError:
                # heartbeat para manter conexão viva
                yield ":\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Transfer-Encoding": "chunked",
        }
    )



# 🔥 simula o PROXY/IA terminando o processamento

@app.post("/proxy-result")
async def proxy_result(frases: List[str]):

    print("EVENTO RECEBIDO:", frases)

    payload = {
        "type": "highlight",
        "texts": frases
    }

    await event_queue.put(json.dumps(payload))

    print("EVENTO ENVIADO PARA FILA")

    return {"status": "event sent"}
