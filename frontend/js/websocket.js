class DownloadWebSocket {
    constructor(onProgressUpdate, onInitTasks) {
        this.onProgressUpdate = onProgressUpdate;
        this.onInitTasks = onInitTasks;
        this.ws = null;
        this.reconnectTimer = null;
        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/download`;

        console.log(`[WS] Connecting to ${wsUrl}...`);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log("[WS] Connected successfully!");
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === "init_tasks" && this.onInitTasks) {
                    this.onInitTasks(msg.data);
                } else if (msg.type === "progress_update" && this.onProgressUpdate) {
                    this.onProgressUpdate(msg.data);
                }
            } catch (err) {
                console.error("[WS] Error parsing message:", err);
            }
        };

        this.ws.onclose = () => {
            console.warn("[WS] Connection lost. Reconnecting in 3s...");
            this.reconnectTimer = setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = (err) => {
            console.error("[WS] Error:", err);
        };
    }
}
