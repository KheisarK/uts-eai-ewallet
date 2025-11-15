// api.js
const GATEWAY_USER = "http://localhost:3001";  // service-user
const GATEWAY_WALLET = "http://localhost:3002"; // service-wallet

async function apiRequest(url, method = "GET", body = null, token = null) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : null
    });

    let data;
    try {
        data = await response.json();
    } catch (e) {
        throw new Error("Server tidak mengembalikan JSON");
    }

    if (!response.ok) {
        throw new Error(data.message || "Request gagal");
    }

    return data;
}

// ===== USER SERVICE =====
export async function loginUser(email, password) {
    return apiRequest(`${GATEWAY_USER}/users/login`, "POST", { email, password });
}

export async function getProfile(token) {
    return apiRequest(`${GATEWAY_USER}/users/me`, "GET", null, token);
}

// ===== WALLET SERVICE =====
export async function getMyWallet(token) {
    return apiRequest(`${GATEWAY_WALLET}/api/wallets/me`, "GET", null, token);
}
