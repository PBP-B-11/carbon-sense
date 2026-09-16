# Carbon Sense

**Deskripsi Aplikasi :** Aplikasi yang digunakan untuk melacak jejak karbon aktivitas harianmu.

## Daftar Modul Rencana :

### 1. Modul "Carbon Tracker" (Pencatat Jejak Karbon)

- **Fokus Utama:** Fitur inti untuk mencatat emisi harian pengguna (transportasi, listrik, makanan).
- **Komponen CRUD:**
  - **Create:** Menambahkan log aktivitas karbon (misal: "Naik mobil 15 km").
  - **Read:** Menampilkan tabel riwayat aktivitas dan total emisi (Dashboard).
  - **Update:** Mengedit log aktivitas jika salah ketik.
  - **Delete:** Menghapus log dari riwayat.

### 2. Modul "Profile & Environment Settings" (Profil & Widget Udara)

- **Fokus Utama:** Manajemen akun pengguna dan pusat pengaturan lokasi (koordinat kota) yang akan menyuplai data lokasi untuk modul lain.
- **Komponen CRUD:**
  - **Create:** Membuat entitas UserProfile saat pertama kali registrasi (mengatur kota domisili).
  - **Read:** Menampilkan halaman profil, data diri, dan merender widget API.
  - **Update:** Form untuk mengubah Email, Password, Bio, dan Kota Domisili.
  - **Delete:** Fitur hapus akun secara permanen.

### 3. Modul "Eco-Challenges" (Gamifikasi & Tantangan)

- **Fokus Utama:** Menyediakan misi/tantangan harian yang harus diselesaikan pengguna untuk mengurangi emisi.
- **Komponen CRUD:**
  - **Create:** Pengguna mendaftar (join) ke sebuah tantangan yang tersedia.
  - **Read:** Menampilkan daftar tantangan yang aktif (di-filter via API) dan progress bar pengguna.
  - **Update:** Pengguna menekan tombol "Check-in" untuk menambah progress harian tantangan.
  - **Delete:** Membatalkan/berhenti dari tantangan di tengah jalan.

### 4. Modul "Green Community" (Forum & Hot News)

- **Fokus Utama:** Ruang sosial (feed) bagi pengguna untuk berbagi tips dan berdiskusi isu lingkungan.
- **Komponen CRUD:**
  - **Create:** Membuat postingan (tips, diskusi, atau share link berita dari API).
  - **Read:** Menampilkan feed publik berisi postingan pengguna lain.
  - **Update:** Mengedit isi postingan sendiri.
  - **Delete:** Menghapus postingan sendiri.

## Public API/mock API yang akan dipakai :
- Open-Meteo (Weather) : https://open-meteo.com/
- GNews API (Atau Open-Meteo) : https://gnews.io/
- Carbon Calculator : https://www.climatiq.io/docs/api-reference

## Pembagian modul per anggota
Pembagian modul:
- Modul 1: Putu Rizki Manik Widiadnyana (NPM : 2506621900)
- ⁠Modul 2:  Faishal Falih (NPM : 2506612064)
- ⁠Modul 3: M Naufal Abyaz Bawono (NPM : 2506656993)
- ⁠Modul 4: M. Fatih Danika (NPM : 2506532100)