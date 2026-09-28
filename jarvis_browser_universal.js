(() => {
    const BRIDGE = "http://127.0.0.1:8765";

    async function jarvisBrowser(action, data = {}) {
        const response = await fetch(BRIDGE + action, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || "Falha no navegador");
        }

        return result;
    }

    window.JARVIS_BROWSER = {

        open: async (url) => {
            return await jarvisBrowser("/open", { url });
        },

        google: async (query) => {
            return await jarvisBrowser("/open", {
                url:
                    "https://www.google.com/search?q=" +
                    encodeURIComponent(query)
            });
        },

        youtube: async (query) => {
            const url = query
                ? "https://www.youtube.com/results?search_query=" +
                  encodeURIComponent(query)
                : "https://www.youtube.com";

            return await jarvisBrowser("/open", { url });
        },

        back: async () => {
            return await jarvisBrowser("/back");
        },

        forward: async () => {
            return await jarvisBrowser("/forward");
        },

        reload: async () => {
            return await jarvisBrowser("/reload");
        },

        click: async (text) => {
            return await jarvisBrowser("/click-text", { text });
        },

        type: async (text) => {
            return await jarvisBrowser("/type", { text });
        }
    };

    console.log("JARVIS Browser Universal carregado.");
})();
