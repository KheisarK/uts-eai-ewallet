# E-Wallet Microservices System (UTS EAI)

Proyek ini merupakan implementasi sistem **E-Wallet** menggunakan arsitektur **Microservices** yang terdiri dari 4 service terpisah, 1 API Gateway, dan Web Frontend sederhana. Seluruh komunikasi antar komponen dilakukan melalui **API Gateway**. Setiap service memiliki **database terpisah**, sesuai konsep data isolation pada microservices.

## 1. Deskripsi Singkat Proyek

Sistem E-Wallet ini menyediakan fitur:
- Pengelolaan Profil Pengguna
- Pengelolaan Wallet & Saldo
- Transaksi (Top Up, Transfer, Pembayaran, Tarik Saldo)
- Daftar Penerima (Payees)

Menggunakan:
- Flask (Backend Microservices)
- Node.js Express (API Gateway)
- MySQL (Database)
- HTML + JS (Frontend)

## 2. Arsitektur Sistem

Client (Frontend) → API Gateway → user-service / wallet-service / transaction-service / payee-service → Database

## 3. Cara Menjalankan Sistem

### Persiapan
Set environment berikut:
```
DB_HOST=localhost
DB_USER=root
DB_PASS=yourpassword
DB_NAME_USERS=db_users
DB_NAME_WALLETS=db_wallets
DB_NAME_TRANSACTIONS=db_transactions
DB_NAME_PAYEES=db_payees
JWT_SECRET=secret123
```

### Menjalankan Services
```
cd service-user
python app.py

cd service-wallet
python app.py

cd service-transaction
python app.py

cd service-payee
python app.py
```

### Menjalankan API Gateway
```
cd api_gateway
npm install
node index.js
```

### Menjalankan Frontend
```
cd frontend
open index.html
```

## 4. Anggota & Peran

| Nama | Peran | Tanggung Jawab |
|------|--------|----------------|
| Alvi | Backend 1 | user-service, frontend, API Gateway |
| Kheisar | Backend 2 | transaction-service, payee-service, API Gateway, frontend |
| Raiyan | System Analyst 1 | Sequence Diagram, Use Case, ERD, wallet-service |
| Bisma | System Analyst 2 | Sequence Diagram, Architecture, API Spec, Docs API, wallet-service |

## 5. Ringkasan Endpoint

### User-Service
- /users
- /users/me
- /payees

### Wallet-Service
- /wallets/me
- /internal/wallets/*

### Transaction-Service
- /transactions

### Payee-Service
- /payees

Dokumentasi API dapat diakses pada:
```
docs/api/
```

## 6. Struktur Folder
```
uts-eai-ewallet-main/
│  README.md
├── api_gateway/
├── docs/
│   ├── api/
│   └── testing/
├── frontend/
├── service-payee/
├── service-transaction/
├── service-user/
├── service-wallet/
└── sql/
```
