document.addEventListener("DOMContentLoaded", () => {
    const metrikUrlInput = document.getElementById("metrikUrl");
    const autoSyncToggle = document.getElementById("autoSyncToggle");
    const saveBtn = document.getElementById("saveBtn");
    const syncNowBtn = document.getElementById("syncNowBtn");
    const statusDiv = document.getElementById("status");

    // Load saved settings
    chrome.storage.sync.get(["metrikUrl", "autoSyncEnabled"], (data) => {
        if (data.metrikUrl) metrikUrlInput.value = data.metrikUrl;
        autoSyncToggle.checked = !!data.autoSyncEnabled;
    });

    saveBtn.addEventListener("click", () => {
        chrome.storage.sync.set({
            metrikUrl: metrikUrlInput.value,
            autoSyncEnabled: autoSyncToggle.checked
        }, () => {
            showStatus("Pengaturan disimpan!", "green");
        });
    });

    syncNowBtn.addEventListener("click", () => {
        showStatus("Mengambil cookie...", "#007bff");
        
        // Ambil semua cookie di domain ACMT
        chrome.cookies.getAll({ domain: "portalapp.iconpln.co.id" }, (cookies) => {
            let cookieString = cookies.map(c => `${c.name}=${c.value}`).join("; ");
            
            if (!cookieString || cookieString.length < 10) {
                showStatus("Cookie kosong! Harap login ke ACMT dulu.", "red");
                return;
            }

            let targetUrl = metrikUrlInput.value.replace(/\/$/, "");
            let urlObj;
            try {
                urlObj = new URL(targetUrl);
            } catch(e) {
                showStatus("URL METRIK tidak valid!", "red");
                return;
            }
            let domainName = urlObj.hostname.replace("www.", "");
            
            // Tanamkan cookie ACMT ke dalam browser untuk domain Metrik
            chrome.cookies.set({
                url: targetUrl,
                name: "metrik_acmt_session",
                value: encodeURIComponent(cookieString),
                domain: "." + domainName,
                path: "/",
                secure: true,
                sameSite: "no_restriction"
            }, function(cookie) {
                if (chrome.runtime.lastError) {
                    showStatus("❌ Gagal menanam cookie di browser!", "red");
                    console.error("Set Cookie Error:", chrome.runtime.lastError);
                } else {
                    showStatus("✅ Berhasil disinkronkan ke browser Anda!", "green");
                }
            });
        });
    });

    function showStatus(message, color) {
        statusDiv.textContent = message;
        statusDiv.style.color = color;
        setTimeout(() => {
            if (statusDiv.textContent === message) {
                statusDiv.textContent = "";
            }
        }, 4000);
    }
});
