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
        // Coba parsing JSON (bahkan jika status error, untuk mendapatkan pesan error)
        data = await response.json();
    } catch (e) {
        // Jika server mengembalikan respons non-JSON pada error (cth: 500 HTML atau kosong)
        if (!response.ok) throw new Error(response.statusText || "Server error");
        throw new Error("Server tidak mengembalikan JSON");
    }

    // Jika status bukan 2xx, throw error.
    if (!response.ok) {
        // Menggunakan pesan dari service backend (data.message atau data.error)
        throw new Error(data.error || data.message || "Request gagal");
    }
    return data;
}

// =================================================================
// ===== USER SERVICE (via Gateway) =====
// =================================================================
export async function loginUser(phone, password) {
    // Panggil rute /api/users/login di GATEWAY
    return apiRequest(`${GATEWAY_URL}/api/users/login`, "POST", { phone, password }); 
}

export async function getProfile(token) {
    // Panggil rute /api/users/me di GATEWAY
    return apiRequest(`${GATEWAY_URL}/api/users/me`, "GET", null, token);
}

// =================================================================
// ===== WALLET & TRANSACTION SERVICE (via Gateway) =====
// =================================================================
export async function getMyWallet(token) {
    // Panggil rute /api/wallets/me di GATEWAY
    return apiRequest(`${GATEWAY_URL}/api/wallets/me`, "GET", null, token);
}

// 1. Fungsi untuk Top Up (via Gateway)
export async function topupWallet(token, amount) {
    // Memanggil: POST /api/topup
    return apiRequest(`${GATEWAY_URL}/api/topup`, "POST", { amount: amount }, token);
}

// 2. Fungsi untuk Melihat Riwayat Transaksi (via Gateway)
export async function getMyTransactions(token) {
    // Memanggil: GET /api/transactions
    return apiRequest(`${GATEWAY_URL}/api/transactions`, "GET", null, token);
}

// 3. Fungsi untuk Membuat Transfer (via Gateway)
export async function createTransaction(token, receiver_phone, amount) {
    // Memanggil: POST /api/transactions
    return apiRequest(`${GATEWAY_URL}/api/transactions`, "POST", { receiver_phone, amount }, token);
}

// =================================================================
// ===== PAYEE SERVICE (via Gateway) -- TAMBAHAN BARU =====
// =================================================================

// (C)RUD: Mendapatkan semua daftar penerima
export async function getPayees(token) {
    // Memanggil: GET /api/payees
    return apiRequest(`${GATEWAY_URL}/api/payees`, "GET", null, token);
}

// C(R)UD: Membuat penerima baru
export async function createPayee(token, name, account_identifier, provider) {
    // Memanggil: POST /api/payees
    return apiRequest(`${GATEWAY_URL}/api/payees`, "POST", { name, account_identifier, provider }, token);
}

// CR(U)D: Memperbarui penerima
export async function updatePayee(token, id, name, account_identifier, provider) {
    // Memanggil: PUT /api/payees/{id}
    return apiRequest(`${GATEWAY_URL}/api/payees/${id}`, "PUT", { name, account_identifier, provider }, token);
}

// CRU(D): Menghapus penerima
export async function deletePayee(token, id) {
    // Memanggil: DELETE /api/payees/{id}
    return apiRequest(`${GATEWAY_URL}/api/payees/${id}`, "DELETE", null, token);
}


// PERHATIAN: apiRequest diekspor agar bisa diakses oleh fungsi helper/private
export { apiRequest };