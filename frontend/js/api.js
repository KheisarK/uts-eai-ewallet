// api.js (FINAL VERSION)

// HANYA ADA SATU ALAMAT: Alamat Gateway Anda
const GATEWAY_URL = "http://localhost:3000"; // Port dari service-gateway/gateway.py

// Fungsi apiRequest Anda sudah bagus, kita pakai lagi
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
        if (!response.ok) throw new Error(response.statusText || "Server error");
        throw new Error("Server tidak mengembalikan JSON");
    }

    // Jika status bukan 2xx, throw error.
    if (!response.ok) {
        throw new Error(data.error || data.message || "Request gagal");
    }
    return data;
}

// ===== USER SERVICE (via Gateway) =====
export async function loginUser(phone, password) {
    // Panggil rute /api/users/login di GATEWAY
    return apiRequest(`${GATEWAY_URL}/api/users/login`, "POST", { phone, password }); 
}

export async function getProfile(token) {
    // Panggil rute /api/users/me di GATEWAY
    return apiRequest(`${GATEWAY_URL}/api/users/me`, "GET", null, token);
}

// -------------------------------------------------------------
// ===== WALLET & TRANSACTION SERVICE (via Gateway) =====
// -------------------------------------------------------------

export async function getMyWallet(token) {
    // Panggil rute /api/wallets/me di GATEWAY
    return apiRequest(`${GATEWAY_URL}/api/wallets/me`, "GET", null, token);
}

// 1. Fungsi untuk Top Up (Asumsi: Gateway handle CREDIT ke akun sendiri)
export async function topupWallet(token, amount) {
    return apiRequest(`${GATEWAY_URL}/api/topup`, "POST", { amount: amount }, token);
}

// 2. Fungsi untuk Melihat Riwayat Transaksi
export async function getMyTransactions(token) {
    // Panggil rute /api/transactions di GATEWAY
    return apiRequest(`${GATEWAY_URL}/api/transactions`, "GET", null, token);
}

// 3. Fungsi untuk Membuat Transfer (Debit)
export async function createTransaction(token, receiver_phone, amount) {
    // Panggil rute /api/transactions di GATEWAY
    // Gateway akan meneruskan ini ke service-transaction
    return apiRequest(`${GATEWAY_URL}/api/transactions`, "POST", { receiver_phone, amount }, token);
}

// PERHATIAN: Semua fungsi diekspor di sini agar bisa diakses oleh halaman HTML (seperti dashboard.html)
export { apiRequest };