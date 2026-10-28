// background.js

chrome.runtime.onInstalled.addListener(() => {
    // Buat alarm yang berjalan setiap 1 menit
    chrome.alarms.create("acmtHeartbeat", { periodInMinutes: 1.0 });
});

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "acmtHeartbeat") {
        chrome.storage.sync.get(["autoSyncEnabled"], (data) => {
            if (!data.autoSyncEnabled) return; // Skip if toggle is off

            console.log("Mengirim Heartbeat ke portal ACMT untuk mencegah auto-logout...");
            // Ping halaman ACMT untuk menjaga sesi tetap hidup (tambahkan timestamp agar tidak di-cache browser)
            let cacheBuster = "?_ts=" + new Date().getTime();
            fetch("https://portalapp.iconpln.co.id/acmt/Main.htm" + cacheBuster, { 
                method: "HEAD", 
                credentials: "include", // WAJIB agar cookie JSESSIONID ikut terkirim ke server
                cache: "no-store"       // WAJIB agar browser tidak memakai cache
            })
                .then(res => {
                    console.log("Heartbeat sukses, status:", res.status);
                    chrome.cookies.getAll({ domain: "portalapp.iconpln.co.id" }, (cookies) => {
                        let cookieString = cookies.map(c => `${c.name}=${c.value}`).join("; ");
                        if (cookieString.includes("JSESSIONID") || cookieString.includes("ci_session")) {
                            syncToMetrik(cookieString);
                        }
                    });
                })
                .catch(err => console.error("Heartbeat gagal:", err));
        });
    }
});

chrome.cookies.onChanged.addListener((changeInfo) => {
    if (changeInfo.cookie.domain.includes("portalapp.iconpln.co.id")) {
        chrome.storage.sync.get(["autoSyncEnabled"], (data) => {
            if (!data.autoSyncEnabled) return; // Skip if toggle is off

            chrome.cookies.getAll({ domain: "portalapp.iconpln.co.id" }, (cookies) => {
                let cookieString = cookies.map(c => `${c.name}=${c.value}`).join("; ");
                if (cookieString.includes("JSESSIONID") || cookieString.includes("ci_session")) {
                    syncToMetrik(cookieString);
                }
            });
        });
    }
});

function syncToMetrik(cookieString) {
    chrome.storage.sync.get(["metrikUrl", "secretKey"], (data) => {
        if (!data.metrikUrl) {
            console.log("Auto-Sync ditunda: URL METRIK belum disetting di popup.");
            return;
        }

        let targetUrl = data.metrikUrl.replace(/\/$/, "");
        let urlObj;
        try {
            urlObj = new URL(targetUrl);
        } catch(e) {
            console.error("Invalid URL:", targetUrl);
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
                console.error("Gagal menanam cookie ke Metrik:", chrome.runtime.lastError);
            } else {
                console.log("Berhasil menanam cookie ke browser untuk", targetUrl);
            }
        });
    });
}
